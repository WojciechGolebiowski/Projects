import pandas as pd
import numpy as np
import pyreadr
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
from bs4 import BeautifulSoup
import pickle
import re
import os

IDS_FILEPATH = "XXX"
DATASET_NAME = 'LONDON_BIRTHDAY_PARTY'

def obtain_ids(browser,IDS_FILEPATH):
    try:            
        service = Service(r"XXX//chromedriver-win64//chromedriver-win64//chromedriver.exe")
        options = Options()
        options.binary_location = r"XXX//chrome-win64//chrome-win64//chrome.exe"
        browser = webdriver.Chrome(service=service, options=options)
        browser.get("https://www.google.com")
        browser.find_element(By.XPATH, "//button[@id='L2AGLb']").click()
        ids = []
        page_iter = True
        page_num = 1
        while page_iter:
            hyperlink = f'https://www.peerspace.com/s/?map_pref=false&p={page_num}&location=london--uk&a=birthday-party'
            browser.get(hyperlink)
            time.sleep(5)

            page_source = browser.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            target_div = soup.find('div', class_='flex flex-wrap flex-grow ps-row w-100')
            if target_div:
                # Extract all IDs within the div
                ids += [element.get('id') for element in target_div.find_all(True) if element.get('id')]
                page_num += 1
                print(page_num)
            else:
                page_iter = False
    finally:
        # Close the browser
        browser.quit()

    with open(IDS_FILEPATH, "wb") as output:
        pickle.dump(ids,output)

def read_ids(IDS_FILEPATH):
    '''Reads pickle object file with saved ids and returns them as list of values'''

    with open (IDS_FILEPATH, 'rb') as fp:
        list_1 = pickle.load(fp)
    
    return list_1

def data_scraper(IDS_FILEPATH,DATASET_NAME):

    list_of_ids = read_ids(IDS_FILEPATH)
    SHEET = 'XXX/Desktop/WebScrapTutor/' + DATASET_NAME + '.xlsx'

    if os.path.exists(SHEET):
        existing_ids = pd.read_excel(SHEET)["Object ID"].tolist()
        list_of_ids = [item for item in list_of_ids if item not in existing_ids]
    else:
        print("No existing file.. New file will be prepared")

    service = Service(r"XXX//chromedriver-win64//chromedriver-win64//chromedriver.exe")
    options = Options()
    options.binary_location = r"XXX//chrome-win64//chrome-win64//chrome.exe"
    browser = webdriver.Chrome(service=service, options=options)

    browser.get("https://www.google.com")
    browser.find_element(By.XPATH, "//button[@id='L2AGLb']").click()

    all_data = pd.DataFrame()
    for LOCATION_ID in list_of_ids:
        try:
            print(LOCATION_ID)
            hyperlink = f'https://www.peerspace.com/pages/listings/{LOCATION_ID}'
            browser.get(hyperlink)
            time.sleep(2)

            page_source = browser.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            div_texts = [div.get_text(strip=True) for div in soup.find_all('div', class_='margin-sm-left')]
            review =  div_texts[3] if div_texts[3] else np.nan
            people = div_texts[4] if div_texts[4] else np.nan
            duration = div_texts[5] if div_texts[5] else np.nan
            area = div_texts[6] if div_texts[6] else np.nan

            location_name_tag = soup.find('div', class_= re.compile(r'ListingLocation'))
            location = location_name_tag.get_text(strip=True) if location_name_tag else np.nan

            object_name_tag = soup.find('h1', class_='word-wrap no-margin h3')
            object_name = object_name_tag.get_text(strip=True) if object_name_tag else np.nan

            price_name_tag = soup.find('div', class_='price')
            price = price_name_tag.get_text(strip=True) if price_name_tag else np.nan

            amenities_in_elements = soup.find_all('div', class_=['amenity-item'])
            amenities_out_elements = soup.find_all('div', class_='amenity-item missing')
            amenities_in = [amenity.get_text(strip=True) for amenity in amenities_in_elements] if amenities_in_elements else []
            amenities_out = [amenity_missing.get_text(strip=True) for amenity_missing in amenities_out_elements] if amenities_out_elements else []
            #If item appears in both list then remove it from amenities_in
            amenities_in = [item for item in amenities_in if item not in set(amenities_out)]
            # Combine all amenities for unique columns
            all_amenities = set(amenities_in + amenities_out)
            amenities_data = {amenity: True if amenity in amenities_in else False for amenity in all_amenities}

            page_data = {
                        "Object ID": LOCATION_ID,
                        "Object": object_name,
                        "Price": price,
                        "Review": review,
                        "People": people,
                        "Duration": duration,
                        "Area": area,
                        "Location": location,
                    }
            page_data.update(amenities_data)
            all_data = pd.concat([all_data, pd.DataFrame([page_data])], ignore_index=True).reset_index(drop=True)
            time.sleep(7)
        except Exception as e:
            print(f"Error processing item {LOCATION_ID}: {e}")
            continue
    browser.quit()
    if os.path.exists(SHEET):
        old_data = pd.read_excel(SHEET)
        combined_data = pd.concat([old_data,all_data]).drop_duplicates().reset_index(drop=True)
        combined_data.to_excel(SHEET)
        print("Data combined and saved")
    else:
        all_data.to_excel(SHEET)
        print("New Excel Workbook generated")

## FUNCTION CALL
data_scraper(IDS_FILEPATH,DATASET_NAME)

def is_invalid_price(value):
    if pd.isna(value) or value == '•':  # Check for NaN
        return True
    else:
        return False
    
def split_rating_data(value):
    if pd.isna(value):  # Handle NaN values
        return np.nan, np.nan
    try:
        rating, reviews = value.split(" (")
        rating = float(rating)  # Convert rating to float
        reviews = int(reviews.strip(")"))  # Remove closing parenthesis and convert to integer
        return rating, reviews
    except ValueError:  # Handle unexpected formats
        return np.nan, np.nan

def clean_excel(DATASET_NAME):
    SHEET = 'XXX/Desktop/WebScrapTutor/' + DATASET_NAME + '.xlsx'
    df = pd.read_excel(SHEET)
    df['Object ID'] = 'https://www.peerspace.com/pages/listings/' + df['Object ID']
    for col in df.columns[8:]:
        df[col] = df[col].\
            apply(lambda x: 0 if x is False else (1 if not pd.isna(x) and x else x))

    #Handle spaces without opinions
    for i in range(len(df)):
        if is_invalid_price(df.loc[i,"Area"]) & is_invalid_price(df.loc[i,"Duration"]):
            df.loc[i,"Area"] = None
            df.loc[i,"Duration"] = df.loc[i, "People"]
            df.loc[i,"People"] = df.loc[i, "Review"]
            df.loc[i,['Review']] = None
        elif is_invalid_price(df.loc[i,"Area"]):
            df.loc[i,"Area"] = df.loc[i, "Duration"]
            df.loc[i,"Duration"] = df.loc[i, "People"]
            df.loc[i,"People"] = df.loc[i, "Review"]
            df.loc[i,['Review']] = None

    #Split reviews
    df[["rating", "num_reviews"]] = df["Review"].apply(split_rating_data).apply(pd.Series)
    df.drop(columns='Review',axis=1,inplace=True)
    columns = df.columns.tolist()
    new_order = columns[:2] + ["rating", "num_reviews"] + columns[2:-2]  # Reorder columns
    df = df[new_order]
    SHEET_UPD = 'XXX/Desktop/WebScrapTutor/Updated_' + DATASET_NAME + '.xlsx'
    
    df.to_excel(SHEET_UPD)

#FUNCTION CALL
clean_excel(DATASET_NAME)