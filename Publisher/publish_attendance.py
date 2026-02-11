#!/usr/bin/env python3

import sys
import glob
import os
import json
import re
import pyfiglet
import pandas as pd
from utils.canvas_api import (
    get_students, get_assignments, find_assignment,
    update_grade
)

# ---------------------------
# Banner and Intro
# ---------------------------
def print_banner():
    banner = pyfiglet.figlet_format("Canvas Attendance Import", font="slant")
    sep = u'─' * 100
    print(sep)
    print(banner)
    print(sep)
    print()

def display_intro():
    sep = u'─' * 100
    print("Canvas Attendance Import")
    print(" • Source: Google Form CSV")
    print(" • Matching order: SID > Email > Name")
    print(" • Missing students → score = 0")
    print(" • Scores supported: 1/1, 0/1, decimals")
    print(sep)

# ---------------------------
# Normalize name function
# ---------------------------
def normalize_name(name):
    """
    Normalize a student name for comparison:
    - lowercase
    - remove punctuation
    - remove extra spaces
    - convert "Last, First" to "First Last"
    """
    if not name:
        return ""
    
    name = name.lower()
    name = re.sub(r'[^\w\s]', '', name)
    name = ' '.join(name.split())
    if ',' in name:
        parts = name.split(',')
        name = parts[1].strip() + ' ' + parts[0].strip()
    return name

# ---------------------------
# Config Loader
# ---------------------------
def load_config(config_file='../config.json'):
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

# ---------------------------
# CSV Auto-Detection
# ---------------------------
def detect_csv_by_prefix(prefix):
    matches = glob.glob(f"{prefix}*.csv")
    if not matches:
        print(f"Error: No CSV matching '{prefix}*.csv' in {os.getcwd()}")
        sys.exit(1)
    if len(matches) > 1:
        print(f"Error: Multiple CSVs matching '{prefix}*.csv': {matches}")
        sys.exit(1)
    return matches[0]


# ---------------------------
# Parse Attendance CSV (robust)
# ---------------------------
def parse_attendance_csv(path):
    df = pd.read_csv(path)

    SID_COL = "Please type in your full name and SID (e.g., Albert Einstein, 1234567)"
    EMAIL_COL = "Email Address"
    SCORE_COL = "Score"

    for col in [SID_COL, EMAIL_COL, SCORE_COL]:
        if col not in df.columns:
            raise ValueError(f"Missing '{col}' in attendance CSV")

    by_sid = {}
    by_email = {}
    by_name = {}

    for _, row in df.iterrows():
      # ----- Parse score -----
      score = 0
      if pd.notna(row[SCORE_COL]):
          raw = str(row[SCORE_COL]).strip()
          try:
              if '/' in raw:
                  num, den = raw.split('/')
                  score = float(num) / float(den)
              else:
                  score = float(raw)
          except (ValueError, ZeroDivisionError):
              score = 0

      # ----- Extract SID (exact match only) -----
      sid_raw = str(row[SID_COL]).strip()
      sid_match = re.search(r'\b\d{7}\b', sid_raw)
      if sid_match:
          by_sid[sid_match.group(0)] = score

      # ----- Extract Name (keep full CSV value) -----
      name_only = re.sub(r'[\d(),]', '', sid_raw).strip()

      if name_only:
          by_name[normalize_name(name_only)] = score

      # ----- Email fallback -----
      email = str(row[EMAIL_COL]).strip().lower()
      if email:
          by_email[email] = score

    return by_sid, by_email, by_name



# ---------------------------
# Main
# ---------------------------
def main():
    print_banner()
    display_intro()

    config = load_config()

    access_token = config.get('access_token')
    course_id = config.get('course_id')
    assignment_name = config.get('assignment_name')

    if not all([access_token, course_id, assignment_name]):
        print("Error: 'access_token', 'course_id', and 'assignment_name' must be set in config.json")
        sys.exit(1)

    att_csv = detect_csv_by_prefix('CSE30')
    print(f"Attendance CSV: {att_csv}")

    by_sid, by_email, by_name = parse_attendance_csv(att_csv)
    print(f"Parsed {len(by_sid)} SID matches, {len(by_email)} email matches, {len(by_name)} name matches.\n")

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    endpoint = 'https://canvas.ucsc.edu/api/v1'

    students = get_students(course_id, headers, endpoint)
    assigns = get_assignments(course_id, headers, endpoint)
    assign = find_assignment(assigns, assignment_name)

    if not assign:
        print(f"Assignment '{assignment_name}' not found.")
        sys.exit(1)

    updated = 0
    zeroed = 0

    for student in students:
        canvas_sid = str(student.get('sis_user_id', '')).strip()
        canvas_email = str(student.get('login_id', '')).strip().lower()
        canvas_name_raw = str(student.get('sortable_name', ''))

        if ',' in canvas_name_raw:
            last, first = canvas_name_raw.split(',', 1)
            canvas_name_raw = f"{first.strip()} {last.strip()}"

        canvas_name = normalize_name(canvas_name_raw)

        score = None
        matched_by = None

        if canvas_sid and canvas_sid in by_sid:
            score = by_sid[canvas_sid]
            matched_by = 'SID'
        elif canvas_email and canvas_email in by_email:
            score = by_email[canvas_email]
            matched_by = 'Email'
        elif canvas_name and canvas_name in by_name:
            score = by_name[canvas_name]
            matched_by = 'Name'
        else:
            score = 0
            matched_by = 'None (default 0)'
            zeroed += 1

        update_grade(course_id, assign['id'], student['id'], score, headers, endpoint)
        updated += 1

        # Console log for each student
        print(f"[{matched_by}] {student['sortable_name']} → {score}")

    print(f"\nDone.")
    print(f" • Total students updated: {updated}")
    print(f" • Students assigned 0 (not found in CSV): {zeroed}")

if __name__ == '__main__':
    main()
