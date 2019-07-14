import logging
import re
import collections
import struct
import codecs
import binascii
import math
import sys
import enum
import json
import csv
import numpy as np
import pandas as pd
import threading
from pandas import DataFrame


# Global variables
excel_dict = {}
name_dict = {}
import_dict = {}
export_dict = {} 
# exp_file_path = r'C:\Users\kassent\Desktop\UnrealPakSwitch\v4\2\3\output\Octopath_Traveler\Content\GameText\Database\GameTextZH_CN.uexp'
# asset_file_path = r'C:\Users\kassent\Desktop\UnrealPakSwitch\v4\2\3\output\Octopath_Traveler\Content\GameText\Database\GameTextZH_CN.uasset'
# cn_json_file_path = r'C:\Users\kassent\Desktop\GameText\octopath_traveller_cn.json'
exp_file_path = r'C:\Users\kassent\Desktop\UnrealPakSwitch\v4\2\3\output\Octopath_Traveler\Content\GameText\Database\GameTextZH_TW.uexp'
asset_file_path = r'C:\Users\kassent\Desktop\UnrealPakSwitch\v4\2\3\output\Octopath_Traveler\Content\GameText\Database\GameTextZH_TW.uasset'
cn_json_file_path = r'C:\Users\kassent\Desktop\GameText\GameTextZH_TW.json'

root_path = r'C:\Users\kassent\Desktop\UnrealPakSwitch\v4\2\3\output\Octopath_Traveler\Content\GameText\Database\\'
chs_file_name = r'GameTextZH_CN'
cht_file_name = r'GameTextZH_TW'
en_file_name = r'GameTextEN'
jp_file_name = r'GameTextJA'


class ParseException(Exception):
    def __init__(self, msg = ''):
        self.err_msg = msg

    def __str__(self):
        return self.err_msg
    
    def what(self):
        return self.err_msg

class PackException(Exception):
    def __init__(self, msg = ''):
        self.err_msg = msg

    def __str__(self):
        return self.err_msg
    
    def what(self):
        return self.err_msg
    
# File parse utils
def read_uint8(cursor):
    ''' Read a uint16 from the data buffer '''
    return struct.unpack(r'<B', cursor.read(1))[0]

def read_int8(cursor):
    ''' Read a int16 from the data buffer '''
    return struct.unpack(r'<b', cursor.read(1))[0]

def read_uint16(cursor):
    ''' Read a uint16 from the data buffer '''
    return struct.unpack(r'<H', cursor.read(2))[0]

def read_int16(cursor):
    ''' Read a int16 from the data buffer '''
    return struct.unpack(r'<h', cursor.read(2))[0]

def read_uint32(cursor):
    ''' Read a uint32 from the data buffer '''
    return struct.unpack(r'<L', cursor.read(4))[0]

def read_int32(cursor):
    ''' Read a int32 from the data buffer '''
    return struct.unpack(r'<l', cursor.read(4))[0]

def read_uint64(cursor):
    ''' Read a uint64 from the data buffer '''
    return struct.unpack(r'<Q', cursor.read(8))[0]

def read_int64(cursor):
    ''' Read a int64 from the data buffer '''
    return struct.unpack(r'<q', cursor.read(8))[0]

def read_float(cursor):
    ''' Read a single float from the data buffer '''
    return struct.unpack(r'<f', cursor.read(4))[0]

def read_string(cursor):
    length = read_int32(cursor)
    string = '\x00'
    # print('strlen: {0:d}  current cursor: {1:X}'.format(length, cursor.tell()))
    assert length < 65536 and length > -65536
    if length < 0:
        string = cursor.read(length * -2).decode('utf-16')
    elif length > 0:
        string = cursor.read(length).decode('utf-8')
    assert string[-1] == '\x00'
    return string[:-1]

def read_fname(cursor, parse_index = True):
    global name_dict
    idx = read_int32(cursor)
    if parse_index:
        val_index = read_int32(cursor) # unknown int32, maybe name_number?
        if val_index:
            print('current cursor: {0:X} val_index: {1} str: {2}'.format(cursor.tell(), val_index, name_dict[idx].data if idx in name_dict else ''))
    if idx in name_dict:
        return name_dict[idx].data
    return None




def pack_fname(string):
    global name_dict
    for key, value in name_dict.items():
        if string == value.data:
            return pack_int32(key)
    raise PackException('Failed to pack Fname: {0}'.format(string))

def pack_uint8(val):
    return struct.pack(r'<B', val)

def pack_int8(val):
    return struct.pack(r'<b', val)

def pack_uint16(val):
    return struct.pack(r'<H', val)

def pack_int16(val):
    return struct.pack(r'<h', val)

def pack_uint32(val):
    return struct.pack(r'<L', val)

def pack_int32(val):
    return struct.pack(r'<l', val)

def pack_uint64(val):
    return struct.pack(r'<Q', val)

def pack_int64(val):
    return struct.pack(r'<q', val)

def pack_string(string: str) -> bytes:
    bytes_str, bytes_len = None, 0
    if not len(string):
        return pack_int32(0)
    if string.isascii():
        bytes_str = string.encode('utf-8')
        bytes_str += b'\x00'
        print(bytes_str.hex())
        bytes_len = len(bytes_str)
    else:
        bytes_str = string.encode('utf-16')[2:]
        bytes_str += b'\x00\x00'
        print(bytes_str.hex())
        bytes_len = len(bytes_str)
        assert bytes_len % 2 == 0
        bytes_len //= -2
    bytes_output = pack_int32(bytes_len) + bytes_str
    return bytes_output
    


class FText():
    def __init__(self, cursor):
        self.flags = read_uint32(cursor)
        self.history_type = read_int8(cursor)
        if self.history_type == -1:
            self.namespace = ''
            self.key = ''
            self.source_string = ''
        elif self.history_type == 0:
            self.namespace = read_string(cursor)
            self.key = read_string(cursor)
            self.source_string = read_string(cursor)
        else:
            raise ParseException('invalid history type: {0} with cursor at 0x{1:X}'.format(self.history_type, cursor.tell()))
        
    def serialize(self):
        bytes_arr = pack_uint32(self.flags)
        bytes_arr += pack_int8(self.history_type)
        if self.history_type == 0:
            bytes_arr += pack_string(self.namespace)
            bytes_arr += pack_string(self.key) 
            bytes_arr += pack_string(self.source_string)
        return bytes_arr
	
    def __str__(self):
        return 'namespace: {}  key:{}  source_string: {}'.format(self.source_string, self.key, self.source_string)


class FGuid():
    def __init__(self, cursor):
        self.a = read_uint32(cursor)
        self.b = read_uint32(cursor)
        self.c = read_uint32(cursor)
        self.d = read_uint32(cursor)
        
    def serialize(self):
        bytes_arr = pack_uint32(self.a)
        bytes_arr += pack_uint32(self.b)
        bytes_arr += pack_uint32(self.c)
        bytes_arr += pack_uint32(self.d)
        return bytes_arr


class FCustomVersion():
    def __init__(self, cursor):
        self.key = FGuid(cursor)
        self.version = read_int32(cursor)


class FGenerationInfo():
    def __init__(self, cursor):
        self.export_count = read_int32(cursor)
        self.name_count = read_int32(cursor)


class FEngineVersion():
    def __init__(self, cursor):
        self.major = read_uint16(cursor)
        self.minor = read_uint16(cursor)
        self.patch = read_uint16(cursor)
        self.changelist = read_uint32(cursor)
        self.branch = read_string(cursor)


class FCompressedChunk():
    def __init__(self, cursor):
        self.uncompressed_offset = read_int32(cursor)
        self.uncompressed_size = read_int32(cursor)
        self.compressed_offset = read_int32(cursor)
        self.compressed_size = read_int32(cursor)


class FNameEntrySerialized():
    def __init__(self, cursor):
        self.data = read_string(cursor)
        self.non_case_preserving_hash = read_uint16(cursor)
        self.case_preserving_hash = read_uint16(cursor)


class FPackageIndex():
    def __init__(self, cursor):
        self.index = read_int32(cursor)
        # import
        self.import_object_name = FPackageIndex.get_package(self.index)

    @classmethod
    def get_package(cls, index):
        global import_dict
        index = index * (-1) - 1 if index < 0 else index - 1
        if index in import_dict:
            return import_dict[index].object_name
        return str(index)


class FObjectImport():
    def __init__(self, cursor):
        self.class_package = read_fname(cursor)
        self.class_name = read_fname(cursor)
        self.outer_index = FPackageIndex(cursor)
        self.object_name = read_fname(cursor)


class FObjectExport():
    def __init__(self, cursor):
        self.class_index = FPackageIndex(cursor)
        self.super_index = FPackageIndex(cursor)
        self.template_index = FPackageIndex(cursor)
        self.outer_index = FPackageIndex(cursor)
        self.object_name = read_fname(cursor)
        self.save = read_uint32(cursor)
        self.serial_size = read_int64(cursor)
        self.serial_offset = read_int64(cursor)
        self.forced_export = read_int32(cursor)
        self.not_for_client = read_int32(cursor)
        self.not_for_server = read_int32(cursor)
        self.package_guid = FGuid(cursor)
        self.package_flags = read_uint32(cursor)
        self.not_always_loaded_for_editor_game = read_int32(cursor)
        self.is_asset = read_int32(cursor)
        self.first_export_dependency = read_int32(cursor)
        self.serialization_before_serialization_dependencies = read_int32(cursor)
        self.create_before_serialization_dependencies = read_int32(cursor)
        self.serialization_before_create_dependencies = read_int32(cursor)
        self.create_before_create_dependencies = read_int32(cursor)


class FPropertyTag():
    def __init__(self, cursor, read_data: bool):
        self.name, self.val = read_fname(cursor), ''
        assert self.name
        if self.name != 'None':
            self.property_type = read_fname(cursor).strip()
            self.size = read_int32(cursor)
            self.array_index = read_int32(cursor)
            assert self.property_type in 'TextProperty' or self.property_type in 'ObjectProperty'
            self.has_property_guid = read_uint8(cursor) != 0
            self.property_guid = FGuid(cursor) if self.has_property_guid else None
            cursor_pos = cursor.tell()
            if self.property_type in 'TextProperty':
                self.text_data = FText(cursor)
            else: # 'ObjectProperty'
                self.object_data = FPackageIndex(cursor)
            final_pos = cursor_pos + self.size
            cursor.seek(final_pos, 0)
        else:
            raise ValueError('End of FPropertyTag')
    
    def __str__(self):
        if self.property_type in 'TextProperty':
            return self.text_data.source_string
        elif self.property_type in 'ObjectProperty':
            return self.object_data.import_object_name
    
    def serialize(self):
        assert self.property_type in 'TextProperty'
        bytes_result = pack_fname(self.name)
        bytes_result += pack_int32(0)
        bytes_result += pack_fname(self.property_type)
        bytes_result += pack_int32(0)
        bytes_text = self.text_data.serialize()
        bytes_result += pack_int32(len(bytes_text))
        bytes_result += pack_int32(self.array_index)
        bytes_result += pack_int8(self.has_property_guid)
        if self.has_property_guid:
            bytes_result += self.property_guid.serialize()
        bytes_result += bytes_text
        return bytes_result
        

            

class FRowStruct():
    def __init__(self, cursor):
        self.name = read_fname(cursor, False)
        self.name_num = read_int32(cursor)
        self.columns = []
        while True:
            try:
                property_tag = FPropertyTag(cursor, True)
                self.columns.append(property_tag)
            except ValueError:
                break
        # self.update_localization_text()
        
    def update_localization_text(self):
        global excel_dict
        if self.name in excel_dict:
            tr_string = excel_dict[self.name]
            assert len(self.columns) == 1
            text_tag = self.columns[0]
            if text_tag.val != tr_string:
                # 用户翻译了字符串，我们将其更新。
                text_tag.property_data.text.source_string = tr_string
                pass
        pass
            
    def serialize(self):
        bytes_result = pack_fname(self.name)
        bytes_result += pack_int32(self.name_num)
        for property_tag in self.columns:
            bytes_result += property_tag.serialize()
        bytes_result += pack_fname('None')
        bytes_result += pack_int32(0)
        return bytes_result
    

class UObject():
    def __init__(self, cursor):
        self.properties = []
        self.guid = None
        while True:
            try:
                property_tag = FPropertyTag(cursor, True)
                self.properties.append(property_tag)
            except ValueError:
                break
        self.serialize_guid = read_uint32(cursor) != 0
        if self.serialize_guid:
            self.guid = FGuid(cursor)


class UDataTable(UObject):
    def __init__(self, cursor, repack=False):
        super(UDataTable, self).__init__(cursor)
        self.num_rows = read_int32(cursor)
        self.rows, self.repack_bytes = [], None
        self.count = 0
        if repack:
            current_cursor_pos = cursor.tell()
            cursor.seek(0, 0)
            self.repack_bytes = cursor.read(current_cursor_pos)
            print('cur cursor pos: {:X}'.format(cursor.tell()))
        for _ in range(0, self.num_rows):
            row_struct = FRowStruct(cursor)
            self.rows.append(row_struct)
            if repack:
                self.count += 1
                self.repack_bytes += row_struct.serialize()
        if repack:
            checksum_bytes = cursor.read()
            self.repack_bytes += checksum_bytes
        self.final_cursor_pos = cursor.tell()
            
    def save_json_file(self, file):
        text_list = []
        for row in self.rows:
            row_name, row_data, column_data = row.name, {}, {}
            for column in row.columns:
                column_data[column.name] = column.val
            row_data[row_name] = column_data
            text_list.append(row_data) 
        json.dump(text_list, file, ensure_ascii=False, indent=' ')
    
      
    def __iter__(self):
        """读取octopath traveller的翻译文件"""
        for row in self.rows:
            row_name, row_name_num = row.name, row.name_num
            column_data = {}
            for column in row.columns:
                column_data[column.name] = str(column)
            if 'Text' in column_data:
                yield row_name, row_name_num, column_data['Text']   


class ClassList():
    def __init__(self, cls, cursor):
        self.size = read_uint32(cursor)
        self.data = []
        for _ in range(self.size):
            self.data.append(cls(cursor))

class StringList():
    def __init__(self, cursor):
        self.size = read_uint32(cursor)
        self.data = []
        for _ in range(self.size):
            self.data.append(read_string(cursor))

class IntList():
    def __init__(self, cursor):
        self.size = read_uint32(cursor)
        self.data = []
        for _ in range(self.size):
            self.data.append(read_int32(cursor))


class FPackageFileSummary():
    def __init__(self, cursor):
        self.tag = read_int32(cursor)
        self.legacy_file_version = read_int32(cursor)
        self.legacy_ue3_version = read_int32(cursor)
        self.file_version_u34 = read_int32(cursor)
        self.file_version_licensee_ue4 = read_int32(cursor)
        self.custom_version_container = ClassList(FCustomVersion, cursor)
        self.total_header_size = read_int32(cursor)
        self.folder_name = read_string(cursor)
        self.package_flags = read_uint32(cursor)
        self.name_count = read_int32(cursor)
        self.name_offset = read_int32(cursor)
        self.gatherable_text_data_count = read_int32(cursor)
        self.gatherable_text_data_offset = read_int32(cursor)
        self.export_count = read_int32(cursor)
        self.export_offset = read_int32(cursor)
        self.import_count = read_int32(cursor)
        self.import_offset = read_int32(cursor)
        self.depends_offset = read_int32(cursor)
        self.string_asset_references_count = read_int32(cursor)
        self.string_asset_references_offset = read_int32(cursor)
        self.searchable_names_offset = read_int32(cursor)
        self.thumbnail_table_offset = read_int32(cursor)
        self.guid = FGuid(cursor)
        self.generations = ClassList(FGenerationInfo, cursor)
        self.saved_by_engine_version = FEngineVersion(cursor)
        self.compatible_with_engine_version = FEngineVersion(cursor)
        self.compression_flags = read_uint32(cursor)
        self.compressed_chunks = ClassList(FCompressedChunk, cursor)
        self.package_source = read_uint32(cursor)
        self.additional_packages_to_cook = StringList(cursor)
        self.asset_registry_data_offset = read_int32(cursor)
        self.buld_data_start_offset = read_int32(cursor)
        self.world_tile_info_data_offset = read_int32(cursor)
        self.chunk_ids = IntList(cursor)
        self.preload_dependency_count = read_int32(cursor)
        self.preload_dependency_offset = read_int32(cursor)
        # print('tell:{0:X}'.format(cursor.tell()))


def read_localization_file(file_path):
        with open(file_path + '.uasset', 'rb') as assetFile, open(file_path + '.uexp', 'rb') as expFile:
            global name_dict
            name_dict.clear()
            pack_file_summary = FPackageFileSummary(assetFile)
            print(pack_file_summary)
            assetFile.seek(pack_file_summary.name_offset, 0)
            for idx in range(pack_file_summary.name_count):
                name_dict[idx] = FNameEntrySerialized(assetFile)
            print(name_dict)

            global import_dict
            import_dict.clear()
            assetFile.seek(pack_file_summary.import_offset, 0)
            for idx in range(pack_file_summary.import_count):
                import_dict[idx] = FObjectImport(assetFile)
            print(import_dict)

            global export_dict
            export_dict.clear()
            assetFile.seek(pack_file_summary.export_offset, 0)
            for idx in range(pack_file_summary.export_count):
                export_dict[idx] = FObjectExport(assetFile)
            print(export_dict)
            
            asset_length = pack_file_summary.total_header_size                
            for idx, obj_export in export_dict.items():
                export_type = obj_export.class_index.import_object_name
                position = obj_export.serial_offset - asset_length
                expFile.seek(position, 0)
                if export_type in 'DataTable':
                    data_table = UDataTable(expFile, False)
                    final_pos = position + obj_export.serial_size
                    assert final_pos == data_table.final_cursor_pos
                    # with open(r'C:\Users\kassent\Desktop\test\test_23_05.bak', 'wb+') as outputFile:
                    #     outputFile.write(data_table.repack_bytes)
                    for row_id, row_num, row_text in data_table:
                        yield row_id, row_num, row_text


def parse_excel_file(tr_dict, excel_path):
    excel_content = pd.read_excel(excel_path).dropna(axis=0)
    # data = excel_content.loc[:, ['ID','CN']].values
    # print(data)
    for i in excel_content.index.values:
        row_dict = excel_content.loc[i, ['ID', 'CN']].to_dict()
        # for key, value in row_dict.items():
        #     print(key, value)
        tr_dict[row_dict['ID']] = row_dict['CN']



def commit_localization_changes():
    global excel_dict
    chinese_res_path = r'C:\Users\kassent\Desktop\UnrealPakSwitch\v4\2\3\output\Octopath_Traveler\Content\GameText\Database\GameTextZH_CN'
    excel_tr_path = r'C:\Users\kassent\Desktop\localization_bak.xlsx'
    parse_excel_file(excel_dict, excel_tr_path)
    for _ in read_localization_file(chinese_res_path):
        pass
    
    
    


def main():
    
    # commit_localization_changes()
    
    
    en_data, zh_cn_data, zh_tw_data, jp_data = {}, {}, {}, {}
    jp_file_path = root_path + jp_file_name
    for row_id, row_num, row_text in read_localization_file(jp_file_path):
        if row_id not in jp_data:
            jp_data[row_id] = {}
        jp_data[row_id][row_num] = row_text
        
    en_file_path = root_path + en_file_name
    for row_id, row_num, row_text in read_localization_file(en_file_path):
        if row_id not in en_data:
            en_data[row_id] = {}
        en_data[row_id][row_num] = row_text
        
    chs_file_path = root_path + chs_file_name
    for row_id, row_num, row_text in read_localization_file(chs_file_path):
        if row_id not in zh_cn_data:
            zh_cn_data[row_id] = {}
        zh_cn_data[row_id][row_num] = row_text
     
    cht_file_path = root_path + cht_file_name
    for row_id, row_num, row_text in read_localization_file(cht_file_path):
        if row_id not in zh_tw_data:
            zh_tw_data[row_id] = {}
        zh_tw_data[row_id][row_num] = row_text


    output_dict = {}
    output_dict['ID'], output_dict['NID'], output_dict['CN'], output_dict['EN'], output_dict['JP'], output_dict['TW'] = [], [], [], [], [], []
    for row_id, row_data in zh_cn_data.items():
        for row_index, row_text in row_data.items():
            output_dict['ID'].append(row_id)
            output_dict['NID'].append(row_index)
            output_dict['CN'].append(row_text)
            output_dict['EN'].append(en_data[row_id][row_index] if row_id in en_data and row_index in en_data[row_id] else '')
            output_dict['JP'].append(jp_data[row_id][row_index] if row_id in jp_data and row_index in jp_data[row_id] else '')
            output_dict['TW'].append(zh_tw_data[row_id][row_index] if row_id in zh_tw_data and row_index in zh_tw_data[row_id] else '')
    
    frame_data = DataFrame.from_dict(output_dict)
    frame_data.to_excel(r'C:\Users\kassent\Desktop\GameText\localization_2019_07_15.xlsx', encoding='utf-8')
    
    # with open(r'C:\Users\kassent\Desktop\GameText\localization.csv', 'w+', newline='', encoding='utf-8') as csvfile:
    #     spamwriter = csv.writer(csvfile, delimiter=' ',quotechar='|', quoting=csv.QUOTE_MINIMAL)
    #     spamwriter.writerow(['ID', 'CN', 'EN', 'JP', 'TW'])
    #     for row in output_list:
    #         spamwriter.writerow([row['ID'], row['CN'], row['EN'], row['JP'], row['TW']])
            
    
# root_path = r'C:\Users\kassent\Desktop\UnrealPakSwitch\v4\2\3\output\Octopath_Traveler\Content\GameText\Database\\'
# chs_file_name = r'GameTextZH_CN'
# cht_file_name = r'GameTextZH_TW'
# en_file_name = r'GameTextEN'
# ja_file_name = r'GameTextJA'
# root_path = r'C:\Users\kassent\Desktop\UnrealPakSwitch\v4\2\3\output\Octopath_Traveler\Content\GameText\Database\\'
# chs_exp_file_name = r'GameTextZH_CN.uasset'
# chs_asset_file_path = r'GameTextZH_CN.uexp'
# cht_exp_file_name = r'GameTextZH_TW.uasset'
# cht_asset_file_path = r'GameTextZH_TW.uexp'
# en_exp_file_name = r'GameTextEN.uasset'
# en_asset_file_path = r'GameTextEN.uexp'
# ja_exp_file_name = r'GameTextJA.uasset'
# ja_asset_file_path = r'GameTextJA.uexp'
    # with open(asset_file_path, 'rb') as assetFile, open(exp_file_path, 'rb') as expFile:
    #     global name_dict
    #     name_dict.clear()
    #     pack_file_summary = FPackageFileSummary(assetFile)
    #     print(pack_file_summary)
    #     # name_dict = {}
    #     assetFile.seek(pack_file_summary.name_offset, 0)
    #     for idx in range(pack_file_summary.name_count):
    #         name_dict[idx] = FNameEntrySerialized(assetFile)
    #     print(name_dict)

    #     global import_dict
    #     import_dict.clear()
    #     assetFile.seek(pack_file_summary.import_offset, 0)
    #     for idx in range(pack_file_summary.import_count):
    #         import_dict[idx] = FObjectImport(assetFile)
    #     print(import_dict)

    #     global export_dict
    #     export_dict.clear()
    #     assetFile.seek(pack_file_summary.export_offset, 0)
    #     for idx in range(pack_file_summary.export_count):
    #         export_dict[idx] = FObjectExport(assetFile)
    #     print(export_dict)
            
    #     # export_size = sum([obj_export.serial_size for obj_export in export_dict.values()])
    #     asset_length = pack_file_summary.total_header_size
            
    #     for idx, obj_export in export_dict.items():
    #         export_type = obj_export.class_index.import_object_name
    #         position = obj_export.serial_offset - asset_length
    #         expFile.seek(position, 0)
    #         if export_type in 'DataTable':
    #             data_table = UDataTable(expFile)
    #             with open(cn_json_file_path, 'w+', encoding='utf-8') as jsonFile:
    #                 data_table.save_json_file(jsonFile)
    #             print(data_table)
                

if __name__ == '__main__':
    main()



# @enum.unique
# class FPropertyTagData(enum.IntEnum):
#     StructProperty = 0 # (String, FGuid),
#     BoolProperty = 1 # (bool),
#     ByteProperty = 2 # (String),
#     EnumProperty = 3 # (String),
#     ArrayProperty = 4 # (String),
#     MapProperty = 5 # (String, String),
#     SetProperty = 6 # (String),
#     NoData = 7

# @enum.unique
# class FPropertyTagType(enum.IntEnum):
#     BoolProperty = 0 # (bool),
#     StructProperty = 1 # (UScriptStruct),
#     ObjectProperty = 2 # (FPackageIndex),
#     InterfaceProperty = 3 # (UInterfaceProperty),
#     FloatProperty = 4 # (f32),
#     TextProperty = 5 # (FText),
#     StrProperty = 6 # (String),
#     NameProperty = 7 # (String),
#     IntProperty = 8 # (i32),
#     UInt16Property = 9 # (u16),
#     UInt32Property = 10 # (u32),
#     UInt64Property = 11 # (u64),
#     ArrayProperty = 12 # (UScriptArray),
#     MapProperty = 13 # (UScriptMap),
#     ByteProperty = 14 # (u8),
#     EnumProperty = 15 # (Option<String>),
#     SoftObjectProperty = 16 # (FSoftObjectPath),
