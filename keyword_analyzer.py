import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta
from io import BytesIO

# Increase the maximum number of cells that can be styled
pd.set_option("styler.render.max_elements", 1000000)  # Set to 1 million to handle large datasets

# Set page to wide mode at the very beginning
st.set_page_config(layout="wide")

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    return output.read()

def to_excel_column(df, column_name):
    """Convert a single column to Excel with proper formatting"""
    output = BytesIO()
    # Create a new dataframe with just the columns we want
    if column_name == 'Revenue':
        export_df = df[['Keyword', 'Partner', 'Revenue']]
    elif column_name == 'Clicks':
        export_df = df[['Keyword', 'Partner', 'Clicks']]
    elif column_name == 'RPC':
        export_df = df[['Keyword', 'Partner', 'RPC']]
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        export_df.to_excel(writer, index=False)
        # Get the worksheet
        worksheet = writer.sheets['Sheet1']
        # Auto-adjust columns width
        for column in worksheet.columns:
            max_length = 0
            column = [cell for cell in column]
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(cell.value)
                except:
                    pass
            adjusted_width = (max_length + 2)
            worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
    
    output.seek(0)
    return output.read()

def analyze_keywords(df):
    # Convert all column names to strings
    df.columns = df.columns.astype(str)
    
    # First, handle the unnamed columns
    if any('Unnamed' in col for col in df.columns):
        # Get the first two columns regardless of their exact names
        first_col = df.columns[0]
        second_col = df.columns[1]
        df = df.rename(columns={
            first_col: 'PARTNER_NAME',
            second_col: 'QUERY'
        })
    
    # Ensure required columns exist
    if 'PARTNER_NAME' not in df.columns or 'QUERY' not in df.columns:
        raise ValueError("Required columns 'PARTNER_NAME' and 'QUERY' not found in the Excel file")
    
    # Convert PARTNER_NAME and QUERY to string type
    df['PARTNER_NAME'] = df['PARTNER_NAME'].astype(str)
    df['QUERY'] = df['QUERY'].astype(str)
    
    # Get unique partners for filtering
    partners = sorted(df['PARTNER_NAME'].unique())
    
    # Get the sets of columns
    revenue_cols = []
    rpc_cols = []
    clicks_cols = []
    
    for col in df.columns:
        col_str = str(col).upper()
        if 'NET_REVENUE' in col_str:
            revenue_cols.append(col)
        elif 'RPC' in col_str:
            rpc_cols.append(col)
        elif 'CLICKS' in col_str:
            clicks_cols.append(col)
    
    # Sort columns to ensure they're in the right order
    revenue_cols.sort()
    rpc_cols.sort()
    clicks_cols.sort()
    
    if not revenue_cols:
        raise ValueError("No NET_REVENUE columns found in the Excel file")
    
    # Create date labels for the columns
    dates = []
    for i in range(len(revenue_cols)):
        dates.append(f"Day {i+1}")
    
    return df, dates, revenue_cols, rpc_cols, clicks_cols, partners

def find_duplicate_keywords(df, selected_date, revenue_cols, rpc_cols, clicks_cols, selected_partners):
    # Get the index from the selected date
    day_index = int(selected_date.split()[1]) - 1
    
    # Get the corresponding columns for this index
    revenue_col = revenue_cols[day_index]
    rpc_col = rpc_cols[day_index]
    clicks_col = clicks_cols[day_index]
    
    # Clean and convert data for the selected columns
    df[clicks_col] = pd.to_numeric(df[clicks_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df[rpc_col] = pd.to_numeric(df[rpc_col].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0)
    df[revenue_col] = pd.to_numeric(df[revenue_col].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0)
    
    # Create a temporary DataFrame with the metrics we need
    temp_df = pd.DataFrame({
        'PARTNER_NAME': df['PARTNER_NAME'],
        'QUERY': df['QUERY'],
        'REVENUE': df[revenue_col],
        'CLICKS': df[clicks_col],
        'RPC': df[rpc_col]
    })
    
    # Filter by selected partners
    temp_df = temp_df[temp_df['PARTNER_NAME'].isin(selected_partners)]
    
    # Group by keyword to find duplicates
    duplicates = temp_df.groupby('QUERY').agg({
        'PARTNER_NAME': lambda x: ', '.join(sorted(x)),
        'REVENUE': 'sum',
        'CLICKS': 'sum',
        'RPC': lambda x: sum(x) / len(x)  # Average RPC
    }).reset_index()
    
    # Filter for keywords used by multiple partners
    duplicates = duplicates[duplicates['PARTNER_NAME'].str.contains(',')]
    
    if not duplicates.empty:
        # Rename columns to match the format of top performers
        duplicates_df = duplicates.rename(columns={
            'QUERY': 'Keyword',
            'PARTNER_NAME': 'Partners',
            'REVENUE': 'Revenue',
            'CLICKS': 'Total Clicks',
            'RPC': 'Avg RPC'
        })
        
        # Reorder columns
        duplicates_df = duplicates_df[['Keyword', 'Partners', 'Revenue', 'Total Clicks', 'Avg RPC']]
        
        # Sort by Revenue (descending)
        duplicates_df = duplicates_df.sort_values('Revenue', ascending=False)
        return duplicates_df
    return None

def get_top_performers(df, selected_date, revenue_cols, rpc_cols, clicks_cols, selected_partners, min_clicks):
    try:
        # Get the index from the selected date
        day_index = int(selected_date.split()[1]) - 1
        
        # Get the corresponding columns for this index
        revenue_col = revenue_cols[day_index]
        rpc_col = rpc_cols[day_index]
        clicks_col = clicks_cols[day_index]
        
        # Filter by selected partners
        if selected_partners:
            df = df[df['PARTNER_NAME'].isin(selected_partners)]
        
        # Clean and convert data
        df[revenue_col] = pd.to_numeric(df[revenue_col].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0)
        df[clicks_col] = pd.to_numeric(df[clicks_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        df[rpc_col] = pd.to_numeric(df[rpc_col].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0)
        
        # Create clean dataframe
        clean_df = pd.DataFrame({
            'Keyword': df['QUERY'],
            'Partner': df['PARTNER_NAME'],
            'Revenue': df[revenue_col],
            'Clicks': df[clicks_col],
            'RPC': df[rpc_col]
        })
        
        # Apply minimum clicks filter
        clean_df = clean_df[clean_df['Clicks'] >= min_clicks]
        
        if clean_df.empty:
            st.warning(f"No keywords found with {min_clicks} or more clicks. Try lowering the minimum clicks filter.")
            return None, None, None
        
        # Get top performers with consistent column order
        column_order = ['Keyword', 'Partner', 'Revenue', 'Clicks', 'RPC']
        top_revenue = clean_df.nlargest(10, 'Revenue')[column_order]
        top_clicks = clean_df.nlargest(10, 'Clicks')[column_order]
        top_rpc = clean_df.nlargest(10, 'RPC')[column_order]
        
        return top_revenue, top_clicks, top_rpc
    except Exception as e:
        st.error(f"Error in get_top_performers: {str(e)}")
        return None, None, None

def analyze_keyword_trends(df, dates, revenue_cols, rpc_cols, clicks_cols, selected_partners=None, num_days=7):
    """Analyze keyword performance trends over the specified number of days."""
    try:
        # Filter by selected partners if specified
        if selected_partners:
            df = df[df['PARTNER_NAME'].isin(selected_partners)]
        
        # Get the last num_days dates
        recent_dates = dates[-num_days:]
        recent_revenue_cols = revenue_cols[-num_days:]
        recent_clicks_cols = clicks_cols[-num_days:]
        
        # Initialize dictionary to store metrics
        keyword_metrics = {}
        
        # Process each day's data
        for date, rev_col, clicks_col in zip(recent_dates, recent_revenue_cols, recent_clicks_cols):
            # Convert revenue and clicks to numeric, replacing any errors with 0
            df[rev_col] = pd.to_numeric(df[rev_col].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0)
            df[clicks_col] = pd.to_numeric(df[clicks_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
            # Group by keyword and calculate daily metrics
            daily_metrics = df.groupby('QUERY').agg({
                rev_col: 'sum',
                clicks_col: 'sum'
            }).reset_index()
            
            # Update metrics for each keyword
            for _, row in daily_metrics.iterrows():
                keyword = row['QUERY']
                revenue = row[rev_col]
                clicks = row[clicks_col]
                
                if keyword not in keyword_metrics:
                    keyword_metrics[keyword] = {
                        'total_revenue': 0,
                        'total_clicks': 0,
                        'first_revenue': 0,
                        'first_clicks': 0,
                        'last_revenue': 0,
                        'last_clicks': 0
                    }
                
                metrics = keyword_metrics[keyword]
                metrics['total_revenue'] += revenue
                metrics['total_clicks'] += clicks
                
                # Store first day metrics
                if metrics['first_revenue'] == 0:
                    metrics['first_revenue'] = revenue
                    metrics['first_clicks'] = clicks
                
                # Update last day metrics
                metrics['last_revenue'] = revenue
                metrics['last_clicks'] = clicks
        
        # Create trend rows
        trend_rows = []
        for keyword, metrics in keyword_metrics.items():
            if metrics['total_clicks'] >= 30:  # Only include keywords with at least 30 total clicks
                # Calculate revenue trend
                revenue_change = ((metrics['last_revenue'] - metrics['first_revenue']) / metrics['first_revenue'] * 100) if metrics['first_revenue'] > 0 else 0
                
                # Calculate clicks trend
                clicks_change = ((metrics['last_clicks'] - metrics['first_clicks']) / metrics['first_clicks'] * 100) if metrics['first_clicks'] > 0 else 0
                
                # Calculate averages
                avg_daily_revenue = metrics['total_revenue'] / num_days
                avg_daily_clicks = metrics['total_clicks'] / num_days
                avg_rpc = metrics['total_revenue'] / metrics['total_clicks'] if metrics['total_clicks'] > 0 else 0
                
                trend_rows.append({
                    'Keyword': keyword,
                    'Total Revenue': metrics['total_revenue'],
                    'Avg Daily Revenue': avg_daily_revenue,
                    'Total Clicks': metrics['total_clicks'],
                    'Avg Daily Clicks': avg_daily_clicks,
                    'Avg RPC': avg_rpc,
                    'Revenue Trend': f"{revenue_change:+.1f}%",
                    'Clicks Trend': f"{clicks_change:+.1f}%"
                })
        
        if trend_rows:
            trends_df = pd.DataFrame(trend_rows)
            return trends_df
        else:
            st.warning("No keywords found with sufficient data for trend analysis.")
            return None
            
    except Exception as e:
        st.error(f"Error analyzing trends: {str(e)}")
        return None

def get_all_partners_top_keywords(df, selected_date, revenue_cols, rpc_cols, clicks_cols, min_clicks=10):
    # Get the index from the selected date
    day_index = int(selected_date.split()[1]) - 1
    
    # Get the corresponding columns for this index
    revenue_col = revenue_cols[day_index]
    rpc_col = rpc_cols[day_index]
    clicks_col = clicks_cols[day_index]
    
    # Clean and convert data
    df[revenue_col] = pd.to_numeric(df[revenue_col].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0)
    df[clicks_col] = pd.to_numeric(df[clicks_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df[rpc_col] = pd.to_numeric(df[rpc_col].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0)
    
    # Group by keyword across all partners
    grouped_df = df.groupby('QUERY').agg({
        'PARTNER_NAME': lambda x: ', '.join(sorted(set(x))),
        revenue_col: 'sum',
        clicks_col: 'sum',
        rpc_col: 'mean'
    }).reset_index()
    
    # Create clean dataframe
    clean_df = pd.DataFrame({
        'Keyword': grouped_df['QUERY'],
        'Partners': grouped_df['PARTNER_NAME'],
        'Total Revenue': grouped_df[revenue_col],
        'Total Clicks': grouped_df[clicks_col],
        'Average RPC': grouped_df[rpc_col]
    })
    
    # Remove rows containing 'Total'
    clean_df = clean_df[~clean_df['Keyword'].str.contains('Total', case=False, na=False)]
    
    # Apply minimum clicks filter
    clean_df = clean_df[clean_df['Total Clicks'] >= min_clicks]
    
    if clean_df.empty:
        return None
    
    # Get top 20 performers for each metric
    column_order = ['Keyword', 'Partners', 'Total Revenue', 'Total Clicks', 'Average RPC']
    top_revenue = clean_df.nlargest(20, 'Total Revenue')[column_order]
    top_clicks = clean_df.nlargest(20, 'Total Clicks')[column_order]
    top_rpc = clean_df.nlargest(20, 'Average RPC')[column_order]
    
    return top_revenue, top_clicks, top_rpc

def auto_categorize_keywords(keyword):
    """Helper function to automatically categorize keywords based on patterns"""
    keyword = keyword.lower()
    categories = []
    
    # Define comprehensive business category patterns
    patterns = {
        'Cash & Loans': [
            'loan', 'cash', 'money', 'payday', 'lending', 'credit', 'debt', 'mortgage', 'finance',
            'bank', 'borrow', 'lender', 'refinance', 'funding', 'payment', 'invest', 'financial',
            'capital', 'income', 'salary', 'budget', '$', 'dollar', 'free money'
        ],
        'Medical & Health': [
            'doctor', 'medical', 'health', 'hospital', 'clinic', 'treatment', 'surgery', 'physician',
            'healthcare', 'medicine', 'dental', 'emergency', 'care', 'patient', 'symptoms', 'therapy',
            'nurse', 'wellness', 'diet', 'weight loss', 'nutrition', 'vitamin', 'supplement',
            'prescription', 'pharmacy', 'drug', 'rehab', 'recovery', 'mental health', 'counseling'
        ],
        'Legal Services': [
            'injury', 'accident', 'lawyer', 'attorney', 'law firm', 'legal', 'lawsuit',
            'compensation', 'settlement', 'claim', 'sue', 'workers comp', 'disability',
            'criminal', 'defense', 'divorce', 'custody', 'bankruptcy', 'estate', 'will',
            'rights', 'court', 'justice', 'law office', 'legal aid', 'legal help'
        ],
        'Automotive': [
            'car', 'auto', 'vehicle', 'truck', 'dealer', 'repair', 'mechanic', 'transmission',
            'engine', 'brake', 'tire', 'oil change', 'maintenance', 'body shop', 'toyota',
            'honda', 'ford', 'chevrolet', 'chevy', 'nissan', 'hyundai', 'kia', 'bmw',
            'mercedes', 'audi', 'volkswagen', 'vw', 'mazda', 'subaru', 'lexus', 'acura',
            'infiniti', 'jeep', 'dodge', 'chrysler', 'ram', 'cadillac', 'buick', 'gmc',
            'used car', 'new car', 'lease', 'automotive', 'suv', 'sedan', 'pickup', 'van'
        ],
        'Insurance': [
            'insurance', 'policy', 'coverage', 'insure', 'premium', 'claim', 'liability',
            'protection', 'benefits', 'plan', 'life insurance', 'auto insurance', 'health insurance',
            'home insurance', 'renters insurance', 'business insurance', 'medicare', 'medicaid',
            'dental insurance', 'vision insurance', 'insurance quote', 'insurance company'
        ],
        'Home Services': [
            'plumber', 'electrician', 'contractor', 'repair', 'hvac', 'roofing', 'home',
            'house', 'renovation', 'remodel', 'maintenance', 'construction', 'carpet',
            'flooring', 'painting', 'landscaping', 'lawn', 'garden', 'pest control',
            'cleaning', 'maid', 'moving', 'storage', 'security', 'alarm', 'locksmith',
            'window', 'door', 'garage', 'basement', 'kitchen', 'bathroom', 'pool'
        ],
        'Education & Training': [
            'school', 'college', 'university', 'degree', 'course', 'training', 'education',
            'learn', 'study', 'program', 'certificate', 'class', 'online course', 'tutor',
            'student', 'scholarship', 'grant', 'financial aid', 'career', 'job training',
            'certification', 'diploma', 'graduate', 'undergraduate', 'masters', 'phd',
            'vocational', 'technical', 'trade school'
        ],
        'Internet & Technology': [
            'internet', 'wifi', 'broadband', 'fiber', 'network', 'computer', 'laptop',
            'phone', 'mobile', 'tablet', 'data', 'cloud', 'software', 'app', 'website',
            'hosting', 'email', 'tech support', 'wireless', 'cellular', '5g', '4g',
            'provider', 'connection', 'speed', 'unlimited', 'hotspot', 'router', 'modem',
            'streaming', 'download', 'upload', 'bandwidth', 'isp', 'service provider'
        ],
        'Real Estate': [
            'home', 'house', 'apartment', 'condo', 'rent', 'lease', 'buy', 'sell',
            'property', 'real estate', 'realtor', 'agent', 'broker', 'mortgage',
            'housing', 'commercial', 'residential', 'land', 'lot', 'office space',
            'retail space', 'warehouse', 'foreclosure', 'listing', 'mls'
        ],
        'Business Services': [
            'business', 'company', 'service', 'consulting', 'marketing', 'advertising',
            'management', 'accounting', 'tax', 'payroll', 'hr', 'human resources',
            'recruitment', 'hiring', 'staffing', 'office', 'corporate', 'commercial',
            'enterprise', 'startup', 'small business', 'merchant', 'vendor'
        ],
        'Travel & Transportation': [
            'travel', 'flight', 'hotel', 'vacation', 'trip', 'tour', 'cruise',
            'airline', 'airport', 'rental', 'transportation', 'taxi', 'uber',
            'lyft', 'shuttle', 'bus', 'train', 'ticket', 'booking', 'reservation',
            'destination', 'tourism', 'travel agency'
        ]
    }
    
    # Check each category's patterns
    for category, words in patterns.items():
        if any(word in keyword for word in words):
            categories.append(category)
    
    # If no category is found, try to identify common patterns
    if not categories:
        # Check for location-based queries
        location_patterns = ['near me', 'in ', 'at ', 'local', 'city', 'state', 'county']
        if any(pattern in keyword for pattern in location_patterns):
            categories.append('Local Services')
        
        # Check for question-based queries
        question_patterns = ['how', 'what', 'when', 'where', 'why', 'who']
        if any(keyword.startswith(pattern) for pattern in question_patterns):
            categories.append('Information Seeking')
        
        # Check for shopping/price related queries
        shopping_patterns = ['buy', 'price', 'cost', 'cheap', 'affordable', 'discount', 'deal', 'sale']
        if any(pattern in keyword for pattern in shopping_patterns):
            categories.append('Shopping & Deals')
        
        # Check for emergency/urgent queries
        emergency_patterns = ['emergency', '24/7', 'urgent', 'fast', 'quick', 'immediate', 'now']
        if any(pattern in keyword for pattern in emergency_patterns):
            categories.append('Emergency Services')
        
        # If still no category found, mark as General
        if not categories:
            categories.append('General Queries')
    
    return categories

def manage_keyword_categories(df, selected_date, revenue_cols, rpc_cols, clicks_cols):
    # Get the index from the selected date
    day_index = int(selected_date.split()[1]) - 1
    revenue_col = revenue_cols[day_index]
    rpc_col = rpc_cols[day_index]
    clicks_col = clicks_cols[day_index]
    
    # Clean and convert data
    df[revenue_col] = pd.to_numeric(df[revenue_col].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0)
    df[clicks_col] = pd.to_numeric(df[clicks_col].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
    df[rpc_col] = pd.to_numeric(df[rpc_col].astype(str).str.replace('$', '').str.replace(',', ''), errors='coerce').fillna(0)
    
    # Create initial categories
    keyword_data = []
    for _, row in df.iterrows():
        keyword = row['QUERY']
        categories = auto_categorize_keywords(keyword)
        for category in categories:
            keyword_data.append({
                'Category': category,
                'Keyword': keyword,
                'Partner': row['PARTNER_NAME'],
                'Revenue': row[revenue_col],
                'Clicks': row[clicks_col],
                'RPC': row[rpc_col]
            })
    
    # Convert to DataFrame
    categories_df = pd.DataFrame(keyword_data)
    
    # Group by category and keyword
    summary_df = categories_df.groupby(['Category', 'Keyword']).agg({
        'Partner': lambda x: ', '.join(sorted(set(x))),
        'Revenue': 'sum',
        'Clicks': 'sum',
        'RPC': 'mean'
    }).reset_index()
    
    # Calculate category totals
    category_totals = summary_df.groupby('Category').agg({
        'Revenue': 'sum',
        'Clicks': 'sum',
        'Keyword': 'count'
    }).reset_index()
    category_totals = category_totals.rename(columns={'Keyword': 'Keyword Count'})
    category_totals['Avg RPC'] = category_totals['Revenue'] / category_totals['Clicks'].replace(0, 1)
    
    # Sort categories by revenue
    category_totals = category_totals.sort_values('Revenue', ascending=False)
    
    # Display category summary
    st.subheader("Category Performance Summary")
    st.dataframe(
        category_totals.style.format({
            'Revenue': '${:,.2f}',
            'Clicks': '{:,.0f}',
            'Keyword Count': '{:,.0f}',
            'Avg RPC': '${:.2f}'
        }),
        use_container_width=True
    )
    
    # Add category selection
    selected_category = st.selectbox(
        "Select a category to view keywords",
        category_totals['Category'].tolist()
    )
    
    if selected_category:
        # Filter keywords for selected category
        category_keywords = summary_df[summary_df['Category'] == selected_category]
        
        # Add sorting options
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader(f"Keywords in {selected_category}")
        with col2:
            sort_by = st.selectbox(
                "Sort by",
                ["Revenue", "Clicks", "RPC"],
                key="category_sort"
            )
        
        # Sort the dataframe
        category_keywords = category_keywords.sort_values(sort_by, ascending=False)
        
        # Display keywords table
        st.dataframe(
            category_keywords.style.format({
                'Revenue': '${:,.2f}',
                'Clicks': '{:,.0f}',
                'RPC': '${:.2f}'
            }),
            use_container_width=True
        )
        
        # Add download button
        csv = category_keywords.to_csv(index=False)
        st.download_button(
            label=f"Download {selected_category} Category Data",
            data=csv,
            file_name=f"category_{selected_category}_{selected_date}.csv",
            mime="text/csv"
        )

def main():
    st.title("Top Performing Keywords")
    
    # Add instructions before the file uploader
    st.markdown("""
    ### How to Get Your Data:
    1. Go to this URL: [Tableau Dashboard](https://us-west-2b.online.tableau.com/#/site/system1/views/SyndicationRSoCOnlineKWRevDoD/KWByPartner?:iid=3)
    2. In the top left, click on the "KW by Partner" tab
    3. In the top right, click "Cross Tab"
    4. Select "Download 'Query by Partner Tab' as CSV"
    5. Save as an Excel Workbook (.xlsx)
    6. Upload the Excel file below
    """)
    
    uploaded_file = st.file_uploader("Choose your Excel file", type=['xlsx', 'xls'])
    
    if uploaded_file is not None:
        try:
            # Read the Excel file with explicit dtype for string columns
            df = pd.read_excel(
                uploaded_file,
                dtype={
                    'PARTNER_NAME': str,
                    'QUERY': str
                }
            )
            
            # Analyze the data
            df, dates, revenue_cols, rpc_cols, clicks_cols, partners = analyze_keywords(df)
            
            # Create filters at the top
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                # Add "Select All Partners" checkbox
                select_all_partners = st.checkbox("Select All Partners", value=True)
                
                if select_all_partners:
                    selected_partners = partners
                else:
                    selected_partners = st.multiselect(
                        "Select Partners",
                        partners,
                        default=partners[:5] if len(partners) > 5 else partners
                    )
            
            with col2:
                date_col1, date_col2 = st.columns(2)
                with date_col1:
                    # Add "All Dates" checkbox
                    select_all_dates = st.checkbox("Use All Dates", value=False)
                    
                    if select_all_dates:
                        selected_date = dates[-1]  # Use the last date for single-day views
                        st.info("Using data from all available dates")
                    else:
                        selected_date = st.selectbox(
                            "Select Date",
                            dates,
                            index=len(dates)-1
                        )
                
                with date_col2:
                    # Add date range selector for trends
                    trend_days = st.number_input(
                        "Trend Days",
                        min_value=1,
                        max_value=len(dates),
                        value=min(7, len(dates)),
                        help="Number of days to analyze for trends"
                    )
            
            with col3:
                min_clicks = st.number_input(
                    "Minimum Clicks",
                    min_value=0,
                    value=30,
                    step=10,
                    help="Filter keywords by minimum number of clicks"
                )
            
            if selected_partners:
                # Create tabs for different analyses
                tabs = st.tabs([
                    "Top Performers",
                    "All Partners Analysis",
                    "Keyword Trends",
                    "Keyword Categories",
                    "Instructions"  # Added new tab
                ])
                
                # Tab 1: Top Performers
                with tabs[0]:
                    top_revenue, top_clicks, top_rpc = get_top_performers(
                        df, selected_date, revenue_cols, rpc_cols, clicks_cols, 
                        selected_partners, min_clicks
                    )
                    
                    if top_revenue is not None:
                        st.subheader("Top Revenue")
                        
                        # Create columns for the table and download button
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.dataframe(
                                top_revenue.style.format({
                                    'Revenue': '${:,.2f}',
                                    'RPC': '${:,.2f}',
                                    'Clicks': '{:,.0f}'
                                }),
                                use_container_width=True
                            )
                        
                        with col2:
                            st.download_button(
                                label="📥 Download Revenue",
                                data=to_excel_column(top_revenue, 'Revenue'),
                                file_name=f"revenue_only_{selected_date}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                help="Download just the Revenue data as Excel"
                            )
                        
                        st.subheader("Top Clicks")
                        
                        # Create columns for the table and download button
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.dataframe(
                                top_clicks.style.format({
                                    'Revenue': '${:,.2f}',
                                    'RPC': '${:,.2f}',
                                    'Clicks': '{:,.0f}'
                                }),
                                use_container_width=True
                            )
                        
                        with col2:
                            st.download_button(
                                label="📥 Download Clicks",
                                data=to_excel_column(top_clicks, 'Clicks'),
                                file_name=f"clicks_only_{selected_date}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                help="Download just the Clicks data as Excel"
                            )
                        
                        st.subheader("Top RPC")
                        
                        # Create columns for the table and download button
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.dataframe(
                                top_rpc.style.format({
                                    'Revenue': '${:,.2f}',
                                    'RPC': '${:,.2f}',
                                    'Clicks': '{:,.0f}'
                                }),
                                use_container_width=True
                            )
                        
                        with col2:
                            st.download_button(
                                label="📥 Download RPC",
                                data=to_excel_column(top_rpc, 'RPC'),
                                file_name=f"rpc_only_{selected_date}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                help="Download just the RPC data as Excel"
                            )
                        
                        # Add a separator before the combined download
                        st.markdown("---")
                        
                        # Add download button for all data combined
                        combined_results = pd.concat([
                            top_revenue.assign(Category='Top Revenue', Date=selected_date),
                            top_clicks.assign(Category='Top Clicks', Date=selected_date),
                            top_rpc.assign(Category='Top RPC', Date=selected_date)
                        ])
                        
                        st.download_button(
                            label="📥 Download All Data",
                            data=to_excel(combined_results),
                            file_name=f"all_data_{selected_date}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            help="Download all data combined as Excel"
                        )
                
                # Tab 2: All Partners Analysis
                with tabs[1]:
                    st.subheader("Top Keywords Across All Partners")
                    all_partners_results = get_all_partners_top_keywords(
                        df, selected_date, revenue_cols, rpc_cols, clicks_cols, min_clicks
                    )
                    
                    if all_partners_results:
                        top_revenue_all, top_clicks_all, top_rpc_all = all_partners_results
                        
                        st.subheader("By Revenue")
                        st.dataframe(
                            top_revenue_all.style.format({
                                'Total Revenue': '${:,.2f}',
                                'Average RPC': '${:,.2f}'
                            }),
                            use_container_width=True
                        )
                        
                        st.subheader("By Clicks")
                        st.dataframe(
                            top_clicks_all.style.format({
                                'Total Revenue': '${:,.2f}',
                                'Average RPC': '${:,.2f}'
                            }),
                            use_container_width=True
                        )
                        
                        st.subheader("By RPC")
                        st.dataframe(
                            top_rpc_all.style.format({
                                'Total Revenue': '${:,.2f}',
                                'Average RPC': '${:,.2f}'
                            }),
                            use_container_width=True
                        )
                
                # Tab 3: Keyword Trends
                with tabs[2]:
                    st.subheader(f"Keyword Performance Trends ({trend_days} Days)")
                    trends_df = analyze_keyword_trends(
                        df, dates, revenue_cols, rpc_cols, clicks_cols, 
                        selected_partners if not select_all_partners else None,
                        trend_days
                    )
                    
                    if trends_df is not None:
                        # Add sorting options
                        sort_by = st.selectbox(
                            "Sort by",
                            ["Total Revenue", "Total Clicks", "Avg RPC", "Revenue Trend", "Clicks Trend"]
                        )
                        
                        # Sort the dataframe
                        if sort_by in ["Revenue Trend", "Clicks Trend"]:
                            # Remove the % sign and convert to float for sorting
                            trends_df[sort_by + "_Value"] = trends_df[sort_by].str.rstrip('%').astype('float') / 100
                            trends_df = trends_df.sort_values(sort_by + "_Value", ascending=False)
                            trends_df = trends_df.drop(columns=[sort_by + "_Value"])
                        else:
                            trends_df = trends_df.sort_values(sort_by, ascending=False)
                        
                        st.dataframe(
                            trends_df.style.format({
                                'Total Revenue': '${:,.2f}',
                                'Avg Daily Revenue': '${:,.2f}',
                                'Total Clicks': '{:,.0f}',
                                'Avg Daily Clicks': '{:,.1f}',
                                'Avg RPC': '${:.2f}'
                            }),
                            use_container_width=True
                        )
                        
                        # Add download button
                        csv = trends_df.to_csv(index=False)
                        st.download_button(
                            label="Download Trends Data",
                            data=csv,
                            file_name=f"keyword_trends_{trend_days}_days.csv",
                            mime="text/csv"
                        )
                
                # Tab 4: Keyword Categories
                with tabs[3]:
                    manage_keyword_categories(df, selected_date, revenue_cols, rpc_cols, clicks_cols)
                
                # Tab 5: Instructions
                with tabs[4]:
                    st.header("How to Get Your Data")
                    st.markdown("""
                    Follow these steps to get your keyword data:
                    
                    1. Go to this URL: [Tableau Dashboard](https://us-west-2b.online.tableau.com/#/site/system1/views/SyndicationRSoCOnlineKWRevDoD/KWByPartner?:iid=3)
                    2. In the top left, click on the "KW by Partner" tab
                    3. In the top right, click "Cross Tab"
                    4. Select "Download 'Query by Partner Tab' as CSV"
                    5. Save as an Excel Workbook (.xlsx)
                    6. Open the KW Tool and upload the Excel file
                    
                    ### Tips:
                    - Make sure to save the file as .xlsx format
                    - The file should contain columns for PARTNER_NAME, QUERY, NET_REVENUE, RPC, and CLICKS
                    - You can select multiple partners to analyze at once
                    - Use the minimum clicks filter to focus on keywords with significant traffic
                    """)
            else:
                st.warning("Please select at least one partner to analyze data.")
            
            # Add DataFrame information at the bottom
            st.markdown("---")
            st.subheader("DataFrame Information")
            st.write("Original DataFrame columns:", list(df.columns))
            st.write("DataFrame info:")
            st.write(df.info())
                
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.write("Debug info:")
            st.write(e)
            import traceback
            st.write(traceback.format_exc())

if __name__ == "__main__":
    main() 