import pandas as pd

df = pd.read_csv("example.csv")

df.drop(columns=["Date, Time Started"], inplace=True)
df.drop(columns=["Visit Time Hours"], inplace=True)

df['Visits'] = df['Student'].str.split(': ').str[1]
df.dropna(subset=['Student'], inplace=True)
df['Visits'] = df['Visits'].shift(periods=-1)
df.dropna(subset=['Student ID'], inplace=True)

df['First Name'] = df['Student'].str.split(', ').str[1]
df['Last Name'] = df['Student'].str.split(', ').str[0]
df.drop(columns=["Student"], inplace=True)

# df.rename(columns={'Subject/Course/Section': 'Section'}, inplace=True)
df = df[['Subject/Course/Section', 'Last Name', 'First Name','Student ID', 'Visits','Major', 'Email']]

# Forward fill NaN values in Subject/Course/Section with previous non-NaN value
df['Subject/Course/Section'] = df['Subject/Course/Section'].ffill()

df['Student ID'] = df['Student ID'].astype("string").str.replace(".0", "")
df['Student ID'] = '0' + df['Student ID']
df['Visits'] = df['Visits'].astype("int")

df[['Subject','Course','Section']] = df['Subject/Course/Section'].str.split(' ', expand=True)

df['Sum Visits'] = None
df['Total Visits'] = None

for Subject, subject_group in df.groupby('Subject'):
    print(Subject)
    for course, course_group in subject_group.groupby('Course'):
        print(course)
        sum_visits = course_group['Visits'].sum()
        last_index = course_group.index[-1]
        df.at[last_index, 'Sum Visits'] = sum_visits
    # Calculate total visits as sum of all 'Sum Visits' for this subject
    total_visits = subject_group['Visits'].sum()
    last_index = subject_group.index[-1]
    df.at[last_index, 'Total Visits'] = total_visits

# Reset index and add empty rows after each subject
df = df.reset_index(drop=True)
subject_info = []  # Store (position, course_count, subject_name)

for Subject, subject_group in df.groupby('Subject'):
    num_courses = subject_group['Course'].nunique()  # Count unique courses
    subject_info.append((subject_group.index[-1], num_courses, Subject))
total_sections = 0

# Insert empty rows (in reverse order to avoid index shifting)
for pos, num_courses, subject in reversed(subject_info):
    empty_row = pd.DataFrame({col: [None] for col in df.columns})
    # Add course count to the Course column (or you could use Subject/Course/Section)
    total_sections += num_courses
    empty_row['Subject/Course/Section'] = f"{num_courses} sections"
    # Optionally, you could also add subject name: empty_row['Subject/Course/Section'] = f"{subject} - {num_courses} courses"
    df = pd.concat([df.iloc[:pos+1], empty_row, df.iloc[pos+1:]]).reset_index(drop=True)

# Calculate totals before dropping columns
total_visits = df['Visits'].sum()  # Total number of visits across all subjects

# Add summary row at the very end
summary_row = pd.DataFrame({col: [None] for col in df.columns})
summary_row['Subject/Course/Section'] = f"Total: {total_sections} sections"
summary_row['Sum Visits'] = total_visits
df = pd.concat([df, summary_row], ignore_index=True)

# Keep Course column for coloring, but we'll drop Subject and Section
df.drop(columns=["Subject","Section"], inplace=True)

print(df.head(10))

# Export to CSV first
df.to_csv("converted.csv", index=False)

# Export to Excel with background colors for each course using pandas Styler
excel_file = "converted.xlsx"

# Define a list of colors (light pastel colors that are easy to read)
colors = [
    '#E3F2FD',  # Light Blue
    '#F3E5F5',  # Light Purple
    '#E8F5E9',  # Light Green
    '#FFF3E0',  # Light Orange
    '#FCE4EC',  # Light Pink
    '#E0F2F1',  # Light Teal
    '#FFF9C4',  # Light Yellow
    '#E1BEE7',  # Light Lavender
    '#BBDEFB',  # Light Blue 2
    '#C8E6C9',  # Light Green 2
    '#FFE0B2',  # Light Orange 2
    '#F8BBD0',  # Light Pink 2
]

# Get unique courses and assign colors
unique_courses = df['Course'].dropna().unique()
course_color_map = {course: colors[i % len(colors)] for i, course in enumerate(unique_courses)}

# Create a function to apply background color based on course
def color_by_course(row):
    course = row['Course']
    if pd.notna(course) and course in course_color_map:
        return [f'background-color: {course_color_map[course]}'] * len(row)
    return [''] * len(row)

# Apply styling using pandas Styler
styled_df = df.style.apply(color_by_course, axis=1)

# Export styled dataframe to Excel
styled_df.to_excel(excel_file, index=False, engine='openpyxl')
print(f"\nExcel file with colored courses saved as: {excel_file}")