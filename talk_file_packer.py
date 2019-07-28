import uasset_parser

def main():
	uasset_parser.repack_localization_files_from_excel(uasset_parser.TALK_EXCEL_PATH, uasset_parser.CN_TALK_ASSET_NAME)

if __name__ == '__main__':
    main()