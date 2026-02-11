# Discussion Session Attendance Publisher

This program is designed to import discussion session attendance from a CSV to Canvas.

## Table of Contents

* [Requirements](#requirements)
* [Usage](#usage)
* [Main Program](#main-program-canvas-publisher)

## Requirements

- **Python 3.x**
- Required Libraries:
    - `pyfiglet`
    - `argparse`
    - `requests`

You can install the required dependencies using the following command:

```bash
pip install -r requirements.txt
```

---

## Usage

### Preparing CSV Files

Before using the main program, you must update the notebookgrader CSV to include the Late Grades.

#### Steps to Prepare the CSV File:

1. **Download the Attendance CSV file:**
    - Go to the Discussion Attendance folder provided by the Lead TA and download the response sheet as a CSV
    ![alt text](docs/attendance.png)


2. **Download the CSV file from Canvas:**
    - Navigate to the **Canvas course** and click the **"Grades"** tab in the left sidebar.
      ![Screenshot 2024-12-06 at 12.14.44 AM.png](docs/Screenshot%202024-12-06%20at%2012.14.44%E2%80%AFAM.png)
    - Click the **"Export"** button in the top-right corner and select **"Export Entire Gradebook"** from the dropdown.
      ![Screenshot 2024-12-06 at 12.17.48 AM.png](docs/Screenshot%202024-12-06%20at%2012.17.48%E2%80%AFAM.png)
    - The file will be named with the current year. 


3. **Prepare the updated file:**
    - Move both Canvas and Attendance files into the `Publisher` directory.

      ![alt text](docs/publisherattendance.png)

---

## Main Program: Canvas Publisher

### Config File (`config.json`)

To run the main program, a `config.json` file is required. This file contains the Canvas API access token, course ID, assignment name, and late token ID.

#### Steps to Create `config.json`:

1. **Get the Canvas API Access Token:**
    - Follow the
      instructions [here](https://community.canvaslms.com/t5/Canvas-Basics-Guide/How-do-I-manage-API-access-tokens-in-my-user-account/ta-p/615312).

2. **Get the Canvas Course ID:**
    - Refer to [this guide](https://13kb.helpscoutdocs.com/article/551-how-to-locate-canvas-course-and-section-id) to
      locate your course ID.

3. **Get the Assignment Name**:
    - This is just the name of the attendance assignment as shown on Canvas.

5. **Edit `config.json`:**
    - Add the information as follows:
    - You can ignore the tokens id

   ```json
   {
     "access_token": "your_canvas_access_token",
     "course_id": "your_course_id",
     "assignment_name": "name_of_assignment",
     "tokens_assignment_id": "tokens_id"
   }
   ```

4. Save the file in the root directory of the project.

---

### Running the Program

1. Navigate to the `Publisher` directory:

   ```bash
   cd Publisher
   ```

2. Identify the main Python files:
    - **`publish_attendance.py`:** Publishes discussion attendance grades to Canvas (main program).

___
4. **Run the main program:**

   ```bash
   python publish_attendance.py
   ```
    - Review the output to ensure grades are successfully updated.


## Output

The program may generate errors if:

- The assignment name is not found in Canvas.
- The CSV file is missing or improperly formatted.
- A student is not found in the Canvas course.
- Grades fail to update.

---

## Author

Created by Michelle Wan.