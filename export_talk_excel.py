from uasset_parser import parse_localization_files_to_excel
from uasset_parser import JA_TALK_ASSET_NAME, EN_TALK_ASSET_NAME, CN_TALK_ASSET_NAME, TW_TALK_ASSET_NAME, WK_TALK_ASSET_NAME

def main():
	parse_localization_files_to_excel(JA_TALK_ASSET_NAME, EN_TALK_ASSET_NAME, CN_TALK_ASSET_NAME, TW_TALK_ASSET_NAME, WK_TALK_ASSET_NAME)

if __name__ == '__main__':
    main()