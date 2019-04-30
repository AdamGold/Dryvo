import os

DEBUG_MODE = os.environ.get("FLASK_DEBUG", 1)
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
WORKDAY_DATE_FORMAT = "%Y-%m-%d"
MAXIMUM_PER_PAGE = 100
MOBILE_LINK = "dryvo://auth/"
LOG_RETENTION = "7 days"
PROFILE_SIZE = 200
STAGING_RECEIPT_URL = "https://demo.ezcount.co.il/"
PRODUCTION_RECEIPT_URL = "https://ezcount.co.il/"
RECEIPTS_DEVELOPER_EMAIL = "ronalister@gmail.com"
