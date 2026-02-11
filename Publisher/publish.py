#!/usr/bin/env python3

import sys
import glob
import os
import pyfiglet
import json
import pandas as pd
from utils.canvas_api import (
    get_students, get_assignments, find_assignment,
    update_grade, update_tokens, get_user_profile
)

# Constants
LATE_PENALTY_RATE = 0.2

# ---------------------------
# Banner and Intro
# ---------------------------
def print_banner():
    banner = pyfiglet.figlet_format("Canvas Grade Publisher", font="slant")
    sep = u'─' * 100
    print(sep)
    print(banner)
    print(sep)
    print()


def display_intro():
    sep = u'─' * 100
    print("Canvas Grade Publisher")
    print("Updates grades using:")
    print(" • Downloaded grades CSV (prefix 'CSE30W26') for on-time and late grades")
    print(" • Canvas gradebook export CSV (prefix '2026-') for current token counts")
    print(sep)

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
# CSV Auto-Detection by Prefix
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
# Parse Downloaded Grades CSV
# ---------------------------
def parse_downloaded_grades(path):
    df = pd.read_csv(path)
    required = ['First Name', 'Last Name', 'Email', 'Grade', 'Late Grade']
    # required = ['First Name', 'Last Name', 'Email', 'Grade']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing '{col}' in downloaded grades CSV")

    name_map = {}
    email_map = {}
    for _, row in df.iterrows():
        first = str(row['First Name']).strip() if pd.notna(row['First Name']) else ''
        last = str(row['Last Name']).strip() if pd.notna(row['Last Name']) else ''
        email = str(row['Email']).strip().lower() if pd.notna(row['Email']) else ''

        regular = None
        if pd.notna(row['Grade']):
            try:
                regular = float(row['Grade'])
            except (ValueError, TypeError):
                regular = None
        late = None
        if pd.notna(row['Late Grade']):
            try:
                late = float(row['Late Grade'])
            except (ValueError, TypeError):
                late = None

        entry = {'regular': regular, 'late': late}
        name_map[(first, last)] = entry
        if email:
            email_map[email] = entry
    return name_map, email_map

# ---------------------------
# Parse Gradebook Export CSV for Current Token Counts
# ---------------------------
def parse_gradebook_tokens(path):
    df = pd.read_csv(path)
    if 'SIS Login ID' not in df.columns:
        raise ValueError("Gradebook CSV must include 'SIS Login ID'")
    # Look for column starting with 'Late Submission Tokens'
    token_col = next((c for c in df.columns if c.startswith('Late Submission Tokens')), None)
    if not token_col:
        raise ValueError("Gradebook CSV missing 'Late Submission Tokens' column")

    tokens_map = {}
    for _, row in df.iterrows():
        email = str(row['SIS Login ID']).strip().lower()
        tokens = 0
        if pd.notna(row[token_col]):
            try:
                tokens = int(float(row[token_col]))
            except (ValueError, TypeError):
                tokens = 0
        tokens_map[email] = tokens
    return tokens_map

# ---------------------------
# Grade Computation Logic
# ---------------------------
def compute_final_grade(entry, tokens):
    if entry.get('late') is None:
        return entry.get('regular')
    if tokens > 0:
        return entry['late']
    if entry.get('regular') is None:
        return entry['late'] * (1 - LATE_PENALTY_RATE)
    diff = entry['late'] - entry['regular']
    return entry['regular'] + diff * (1 - LATE_PENALTY_RATE)

# ---------------------------
# Main
# ---------------------------
def main():
    print_banner()
    display_intro()
    config = load_config()

    access_token         = config.get('access_token')
    course_id            = config.get('course_id')
    assignment_name      = config.get('assignment_name')
    tokens_assignment_id = config.get('tokens_assignment_id')
    if not all([access_token, course_id, assignment_name, tokens_assignment_id]):
    # if not all([access_token, course_id, assignment_name]):
        print("Error: 'access_token', 'course_id', 'assignment_name', and 'tokens_assignment_id' must be set in config.json")
        sys.exit(1)

    dl_csv = detect_csv_by_prefix('CSE30W26')
    gb_csv = detect_csv_by_prefix('2026-')
    print(f"Downloaded grades: {dl_csv}\nGradebook export: {gb_csv}")

    name_map, email_map = parse_downloaded_grades(dl_csv)
    tokens_map = parse_gradebook_tokens(gb_csv)
    print(f"Parsed {len(name_map)} downloaded grades and {len(tokens_map)} token counts.")
    # print(f"Parsed {len(name_map)} downloaded grades")

    headers  = {'Content-Type': 'application/json', 'Authorization': f'Bearer {access_token}'}
    endpoint = 'https://canvas.ucsc.edu/api/v1'
    students = get_students(course_id, headers, endpoint)
    assigns  = get_assignments(course_id, headers, endpoint)
    assign   = find_assignment(assigns, assignment_name)
    if not assign:
        print(f"Assignment '{assignment_name}' not found.")
        sys.exit(1)

    for student in students:
        sid = student['id']

        # fetch full profile so we can get their real email address
        profile = get_user_profile(sid, headers, endpoint)
        email = profile.get('login_id', '').strip().lower()

        # now look up grades & tokens by that email
        entry = email_map.get(email)
        print(f"Entry for {student['sortable_name']}: {entry}")
        if not entry:
            sn = student.get('sortable_name','')
            if ', ' in sn:
                last, first = [x.strip() for x in sn.split(', ', 1)]
            else:
                parts = sn.split(); first, last = parts[0], parts[-1]
            entry = name_map.get((first, last))

        tokens = tokens_map.get(email, 0)
        # tokens = 0
        print(f"Tokens for {student['sortable_name']}: {tokens}")
        grade  = compute_final_grade(entry, tokens) if entry else None
        source = 'downloaded'

        if entry and entry.get('late') is not None and tokens > 0:
            new_tokens = tokens - 1
            update_tokens(course_id, tokens_assignment_id, sid, new_tokens, headers, endpoint)
            print(f"Token consumed for {student['sortable_name']}: tokens left {new_tokens}")

        if grade is None:
            # fallback to zero if no entry
            grade = 0
            source = 'fallback'

        update_grade(course_id, assign['id'], sid, grade, headers, endpoint)
        print(f"Updated {student['sortable_name']} to {grade} ({source})")

    print('All done.')

if __name__ == '__main__':
    main()
