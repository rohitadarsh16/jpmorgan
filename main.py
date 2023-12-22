import requests
from bs4 import BeautifulSoup
import pandas as pd
import aiohttp
import asyncio
import re
from aiofiles import open as aio_open
from asyncio import Lock

df = pd.read_excel("companiesDropdown.xlsx")
file_lock = Lock()
async def to_excel(df, filename):
    loop = asyncio.get_event_loop()
    async with file_lock:
        await loop.run_in_executor(None, lambda: df.to_excel(filename, index=False))





async def fetch(session, url, params=None, data=None, headers=None):
    async with session.post(url, params=params, data=data, headers=headers) as response:
        return await response.text()


async def get_last_page(session, fund_id, page):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.5',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://central-webd.proxydisclosure.com',
        'Connection': 'keep-alive',
        'Referer': 'https://central-webd.proxydisclosure.com/WebDisclosure/wdMeetingList',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }

    data = {
        'siteId': 'JPMFunds',
        'fundId': fund_id,
        'fundIdTmp': '',
        'previewkey': '',
        'currentPageNumber': str(page),
        'meetingId': '',
        'sortByColumn': 'COMPANY_NAME',
        'sortingOrder': 'ASC',
        'fundCompNameSection': '',
        'tickerSymbol': '',
        'companyName': '',
        'companyNameStartsWith': '',
        'meetingDate': '',
        'meetingTypeDesc': '',
        'securityId': '',
        'tickerSymbolPage3': '',
        'isin': '',
        'compNamePage2To3': '',
    }

    response = await fetch(session, "https://central-webd.proxydisclosure.com/WebDisclosure/wdMeetingList", data=data, headers=headers)

    soup = BeautifulSoup(response, 'html.parser')
    page_div = soup.find('div', id='pageNbrText')
    if page_div:
        parts = page_div.text.split()
        last_page = parts[-1] if len(parts) > 1 else parts[0]
        last_page_number = int(last_page)
        if last_page == '1':
            data_present = soup.find('td')
            print(data_present.text)
            if data_present.text == 'No Data Found':
                last_page_number = 0
    else:
        last_page_number = 0
    return last_page_number
backup_data = []
async def get_allpage_data(session, fund_company, fund_id, sheet_data):
    global fund_not_has_data
    global backup_data
    last_page_num = await get_last_page(session, fund_id, '1')
    results = []
    print("Last Page Number:", last_page_num)
    for page in range(1, int(last_page_num) + 1):
        page_results = await get_page_data(session, fund_company, fund_id, str(page), sheet_data)
        backup_data.extend(page_results)
        backup_df = pd.DataFrame(backup_data)
        await to_excel(backup_df, "backup.xlsx")
        results.extend(page_results)
    return results

async def get_page_data(session, fund_company, fund_id, page, sheet_data):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.5',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://central-webd.proxydisclosure.com',
        'Connection': 'keep-alive',
        'Referer': 'https://central-webd.proxydisclosure.com/WebDisclosure/wdMeetingList',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }

    data = {
        'siteId': 'JPMFunds',
        'fundId': fund_id,
        'fundIdTmp': '',
        'previewkey': '',
        'currentPageNumber': str(page),
        'meetingId': '',
        'sortByColumn': 'COMPANY_NAME',
        'sortingOrder': 'ASC',
        'fundCompNameSection': '',
        'tickerSymbol': '',
        'companyName': '',
        'companyNameStartsWith': '',
        'meetingDate': '',
        'meetingTypeDesc': '',
        'securityId': '',
        'tickerSymbolPage3': '',
        'isin': '',
        'compNamePage2To3': '',
    }

    response = await fetch(session, 'https://central-webd.proxydisclosure.com/WebDisclosure/wdMeetingList', data=data, headers=headers)

    soup = BeautifulSoup(response, 'html.parser')
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(response)
    td_elements = soup.find_all('td')
    results = []
    tasks = []
    for td in td_elements:
        anchor_tag = td.find('a')
        if anchor_tag:
            company = anchor_tag.text.strip()
            href_parts = re.split(r"(?<!\\)'", anchor_tag['href'])[1::2]
            if len(href_parts) == 7:
                meeting_id, meeting_date, meeting_type_desc, security_id, ticker_symbol_page3, isin, comp_name_page2to3 = href_parts
                comp_name_page2to3 = comp_name_page2to3.strip()
            else:
                meeting_id, meeting_date, meeting_type_desc, security_id, ticker_symbol_page3, isin, comp_name_page2to3 = anchor_tag['href'].split("'")[1::2]
                comp_name_page2to3 = comp_name_page2to3.strip()

            result_id = {
                'fundId': fund_id,
                'meetingId': meeting_id,
                'meetingDate': meeting_date,
                'meetingTypeDesc': meeting_type_desc,
                'securityId': security_id,
                'isin': isin,
                'compNamePage2To3': comp_name_page2to3
            }
             # Instead of calling get_company_data directly, create a task
            task = get_company_data(session, result_id, fund_company, company, sheet_data)
            tasks.append(task)

    # Use asyncio.gather to run the tasks in parallel
    results = await asyncio.gather(*tasks)
    # print(results)
    
    return results

async def get_company_data(session, dict_ids, fund_company, company_name, sheet_data):
    global fund_not_has_data
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-GB,en;q=0.5',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://central-webd.proxydisclosure.com',
        'Connection': 'keep-alive',
        'Referer': 'https://central-webd.proxydisclosure.com/WebDisclosure/wdMeetingList',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }

    data = {
        'siteId': 'JPMFunds',
        'fundId': dict_ids['fundId'],
        'fundIdTmp': '',
        'previewkey': '',
        'meetingId': dict_ids['meetingId'],
        'sortByColumn': 'COMPANY_NAME',
        'sortingOrder': 'ASC',
        'fundCompNameSection': '',
        'tickerSymbol': '',
        'companyName': '',
        'companyNameStartsWith': '',
        'meetingDate': dict_ids['meetingDate'],
        'meetingTypeDesc': dict_ids['meetingTypeDesc'],
        'securityId': dict_ids['securityId'],
        'tickerSymbolPage3': '',
        'isin': dict_ids['isin'],
        'compNamePage2To3': dict_ids['compNamePage2To3'],
    }

    response = await fetch(session, "https://central-webd.proxydisclosure.com/WebDisclosure/wdMeetingDetail", data=data, headers=headers)

    soup = BeautifulSoup(response, 'html.parser')
    table = soup.find('table')
    data_dict = {}
    labels = table.find_all('label', class_='data-field')
    company_data_list = []
    tables = soup.find('table', class_='tbl')
    if tables:
        second_table = tables
        for row in second_table.find_all('tr')[1:]:
            columns = row.find_all('td')
            item, proposal_description, proposal_type, vote, management_recommendation = [column.text.strip() for column in columns]
            data_dict['company'] = company_name
            data_dict['Meeting Date'] = labels[0].text
            data_dict['Meeting Type'] = labels[1].text
            data_dict['Security/CINS'] = labels[2].text
            data_dict['Ticker'] = labels[3].text
            data_dict['Agenda Number'] = labels[4].text
            data_dict['ISIN'] = labels[5].text
            data_dict['Item'] = item
            data_dict['Proposal Description'] = proposal_description
            data_dict['Proposal Type'] = proposal_type
            data_dict['Vote'] = vote
            data_dict['Management Recommendation'] = management_recommendation
            data_dict['Fund Company'] = fund_company
            company_data_list.append(data_dict)
            print(data_dict)
        sheet_data.extend(company_data_list)
        data_sheet = pd.DataFrame(sheet_data)
        capitalize_first_letter = lambda x: x.str.capitalize() if x.dtype == 'object' else x
        data_sheet = data_sheet.apply(capitalize_first_letter)
        if fund_not_has_data:
            data_proxy = pd.DataFrame(fund_not_has_data)
            data_sheet = pd.concat([data_sheet, data_proxy], axis=1)
       
        await to_excel(data_sheet, "extracted.xlsx")
    else:
        print("There are not enough tables.")

    return data_dict

async def process_fund_data(session, fund_company, fund_id, sheet_data, fund_not_has_data):
    print(f"Processing {fund_company}, Fund ID: {fund_id}")

    all_data = await get_allpage_data(session, fund_company, fund_id, sheet_data)

    if all_data:
        # Create a single DataFrame for all data
        total_data_df = pd.DataFrame(all_data)

        # Save the DataFrame to Excel using aiofiles for asynchronous file writing
        await to_excel(total_data_df, "totaldata.xlsx")
    else:
        print("There are not enough data.")
        fund_not_has_data.append(fund_company)
        data_proxy = pd.DataFrame(fund_not_has_data)
        await to_excel(data_proxy, "prroxy.xlsx")

sheet_data = []
fund_not_has_data = []
async def main():
    global sheet_data
    global fund_not_has_data

    async with aiohttp.ClientSession() as session:
        for fund_id in df['Fund']:
            if fund_id == '0' or fund_id == '@@-$$-@@-$$-@@':
                continue

            fund_company = df[df['Fund'] == fund_id]['Company Name'].values[0]
            await process_fund_data(session, fund_company, fund_id, sheet_data, fund_not_has_data)

if __name__ == "__main__":
    asyncio.run(main())