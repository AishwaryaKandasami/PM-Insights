import os
from dotenv import load_dotenv
load_dotenv(override=True)

token = os.getenv("NOTION_TOKEN")
page_id = os.getenv("NOTION_PAGE_ID")

print(f"NOTION_TOKEN: {'[SET]' if token else '[NOT SET]'}")
print(f"NOTION_PAGE_ID: {page_id if page_id else '[NOT SET]'}")
