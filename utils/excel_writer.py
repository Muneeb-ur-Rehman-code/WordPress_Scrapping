import pandas as pd
from pathlib import Path
from datetime import datetime

class ExcelWriter:
    """Handle writing scraped coupon data to Excel files"""
    
    def __init__(self, filename='scraped_coupons.xlsx', sheet_name='coupons'):
        self.filename = filename
        self.sheet_name = sheet_name
    
    def save_coupons(self, coupons_data, mode='append'):
        """
        Save coupons to Excel file
        
        Args:
            coupons_data (list): List of coupon dictionaries
            mode (str): 'append' or 'overwrite'
        """
        if not coupons_data:
            print("⚠️  No data to save")
            return
        
        # Create DataFrame
        df_new = pd.DataFrame(coupons_data)
        
        # Reorder columns to match specification
        column_order = [
            'source', 'scraped_date', 'store_name', 'title', 'description', 
            'coupon_code', 'deal_type', 'expiry_date', 
            'coupon_url', 'category'
        ]
        
        # Ensure all columns exist
        for col in column_order:
            if col not in df_new.columns:
                df_new[col] = ''

        # Fill scraped_date for new rows with today's date if not provided
        try:
            today = datetime.now().date().isoformat()
            df_new['scraped_date'] = df_new['scraped_date'].apply(
                lambda x: x if pd.notna(x) and str(x).strip() != '' else today
            )
        except Exception:
            df_new['scraped_date'] = datetime.now().date().isoformat()
        
        df_new = df_new[column_order]
        
        # Check if file exists
        file_path = Path(self.filename)
        
        if file_path.exists() and mode == 'append':
            # Read existing data
            try:
                df_existing = pd.read_excel(self.filename, sheet_name=self.sheet_name)
                
                print(f"📊 Existing entries: {len(df_existing)}")
                print(f"📊 New entries: {len(df_new)}")
                
                # Combine data
                df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                
                print(f"📊 Combined entries (before dedup): {len(df_combined)}")
                
                # DEDUPLICATION: Check ALL fields (except scraped_date) to determine duplicates
                # If ALL these fields match, it's a duplicate; otherwise it's unique
                dedup_columns = [
                    'source', 'store_name', 'title', 'description', 
                    'coupon_code', 'deal_type', 'expiry_date', 
                    'coupon_url', 'category'
                ]
                
                # Count before deduplication
                before_count = len(df_combined)
                
                # Remove duplicates (keeps last occurrence)
                df_combined = df_combined.drop_duplicates(subset=dedup_columns, keep='last')
                
                # Count after deduplication
                after_count = len(df_combined)
                duplicates_removed = before_count - after_count
                
                print(f"📊 Duplicates removed: {duplicates_removed}")
                print(f"📊 Final entries (after dedup): {after_count}")
                
                df_final = df_combined
                print(f"✅ Appended {len(df_new)} new entries → {len(df_final)} total after deduplication\n")
                
            except Exception as e:
                print(f"⚠️  Could not read existing file: {e}")
                print(f"⚠️  Writing new file instead...\n")
                df_final = df_new
        else:
            df_final = df_new
            print(f"📝 Creating new file with {len(df_new)} entries\n")
        
        # Write to Excel
        try:
            with pd.ExcelWriter(self.filename, engine='openpyxl', mode='w') as writer:
                df_final.to_excel(writer, sheet_name=self.sheet_name, index=False)
                
                # Auto-adjust column widths
                worksheet = writer.sheets[self.sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter

                    # Header name (first cell in the column)
                    try:
                        header = str(column[0].value).strip().lower()
                    except Exception:
                        header = ''

                    for cell in column:
                        try:
                            cell_len = len(str(cell.value)) if cell.value is not None else 0
                            if cell_len > max_length:
                                max_length = cell_len
                        except Exception:
                            pass

                    # Set column width caps
                    if header == 'description':
                        cap = 120
                    elif header == 'coupon_url':
                        cap = 200  # WIDE for long URLs
                    else:
                        cap = 60

                    adjusted_width = min(max_length + 2, cap)
                    # Ensure a sensible minimum width
                    if adjusted_width < 10:
                        adjusted_width = 10

                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            print(f"✅ Successfully saved to {self.filename}")
            print(f"📊 Total entries in file: {len(df_final)}\n")
            
        except Exception as e:
            print(f"❌ Error saving to Excel: {e}")
            import traceback
            traceback.print_exc()