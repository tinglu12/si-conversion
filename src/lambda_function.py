import json
import base64
import pandas as pd
from io import BytesIO
import zipfile

def process_conversion(csv_content):
    """
    Process CSV content and return converted DataFrames
    """
    # Read CSV into pandas DataFrame
    df = pd.read_csv(BytesIO(csv_content))
    
    # Process the data (your existing logic)
    df.drop(columns=["Date, Time Started"], inplace=True)
    df.drop(columns=["Visit Time Hours"], inplace=True)
    
    df['Visits'] = df['Student'].str.split(': ').str[1]
    df.dropna(subset=['Student'], inplace=True)
    df['Visits'] = df['Visits'].shift(periods=-1)
    df.dropna(subset=['Student ID'], inplace=True)
    
    df['First Name'] = df['Student'].str.split(', ').str[1]
    df['Last Name'] = df['Student'].str.split(', ').str[0]
    df.drop(columns=["Student"], inplace=True)
    
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
    
    return df


def lambda_handler(event, context):
    """
    API Gateway Lambda handler that accepts CSV file and returns downloadable converted files
    
    Query Parameters:
    - format=zip (default): Returns ZIP file with both CSV and Excel
    - format=csv: Returns only CSV file
    - format=xlsx: Returns only Excel file
    
    Request Body:
    - Base64-encoded CSV: {"csv_data": "base64_encoded_string"}
    """
    
    try:
        # Get query parameters
        query_params = event.get('queryStringParameters') or {}
        file_format = query_params.get('format', 'zip').lower()
        
        # Parse the request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Check if CSV data is base64-encoded
        if 'csv_data' in body:
            csv_content = base64.b64decode(body['csv_data'])
        # Check if it's a direct file upload (multipart/form-data)
        elif 'csv_file' in body:
            csv_content = base64.b64decode(body['csv_file'])
        # Check if body is already the CSV content (raw binary)
        elif isinstance(body, str):
            csv_content = base64.b64decode(body)
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'CSV data not found. Send CSV as base64-encoded string in "csv_data" field.'
                })
            }
        
        # Process the conversion
        df = process_conversion(csv_content)
        
        # Generate CSV output
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        csv_data = csv_buffer.getvalue()
        
        # Generate Excel output with colors
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
        
        # Export styled dataframe to Excel buffer
        excel_buffer = BytesIO()
        styled_df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        excel_data = excel_buffer.getvalue()
        
        # Return file based on format parameter
        if file_format == 'csv':
            # Return CSV file
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'text/csv',
                    'Content-Disposition': 'attachment; filename="converted.csv"',
                    'Access-Control-Allow-Origin': '*'
                },
                'isBase64Encoded': True,
                'body': base64.b64encode(csv_data).decode('utf-8')
            }
        elif file_format == 'xlsx':
            # Return Excel file
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'Content-Disposition': 'attachment; filename="converted.xlsx"',
                    'Access-Control-Allow-Origin': '*'
                },
                'isBase64Encoded': True,
                'body': base64.b64encode(excel_data).decode('utf-8')
            }
        else:
            # Default: Return ZIP file with both files
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr('converted.csv', csv_data)
                zip_file.writestr('converted.xlsx', excel_data)
            zip_buffer.seek(0)
            zip_data = zip_buffer.getvalue()
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/zip',
                    'Content-Disposition': 'attachment; filename="converted_files.zip"',
                    'Access-Control-Allow-Origin': '*'
                },
                'isBase64Encoded': True,
                'body': base64.b64encode(zip_data).decode('utf-8')
            }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }

