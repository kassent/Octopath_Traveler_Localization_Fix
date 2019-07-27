import os
import re
import collections
import struct
import codecs
import binascii
import math
import sys
import enum
import json
import numpy as np
import pandas as pd
import threading
import datetime
from pandas import DataFrame


ROOT_FOLDER = os.path.dirname(__file__)
SOURCE_FOLDER = os.path.join(ROOT_FOLDER, 'Text\\Database\\')
TEXT_EXCEL_PATH = os.path.join(ROOT_FOLDER, r'GameTextZH_CN.xlsx')
TALK_EXCEL_PATH = os.path.join(ROOT_FOLDER, r'TalkData_ZH_CH.xlsx')
OUTPUT_FOLDER = os.path.join(ROOT_FOLDER, 'Output\\')

EN_TALK_ASSET_NAME = r'TalkData_EN'
JA_TALK_ASSET_NAME = r'TalkData_JA'
CN_TALK_ASSET_NAME = r'TalkData_ZH_CH'
TW_TALK_ASSET_NAME = r'TalkData_ZH_TW'
WK_TALK_ASSET_NAME = r'TalkData_WK'

EN_TEXT_ASSET_NAME = r'GameTextEN'
JA_TEXT_ASSET_NAME = r'GameTextJA'
CN_TEXT_ASSET_NAME = r'GameTextZH_CN'
TW_TEXT_ASSET_NAME = r'GameTextZH_TW'
WK_TEXT_ASSET_NAME = r'GameTextWK'

# Global variables
# 每次读取翻译文件，这些全局变量都会被清空重写。
excel_dict = {}
name_dict = {}
import_dict = {}
export_dict = {} 

class ParseFileError(Exception):
    def __init__(self, msg = ''):
        self.err_msg = msg

    def __str__(self):
        return self.err_msg
    
    def what(self):
        return self.err_msg

class PackFileError(Exception):
    def __init__(self, msg = ''):
        self.err_msg = msg

    def __str__(self):
        return self.err_msg
    
    def what(self):
        return self.err_msg
    
# 一些二进制解包函数。
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
        read_int32(cursor) # unknown int32, maybe name_number?
    if idx in name_dict:
        return name_dict[idx].data
    return None



# 一些二进制打包函数。
def pack_fname(string, index=0):
    global name_dict
    for key, value in name_dict.items():
        if string == value.data:
            return pack_int32(key) + pack_int32(index)
    raise PackFileError('Failed to pack Fname: {0}'.format(string))

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
    if not len(string):
        return pack_int32(0)
    bytes_str, bytes_len = bytearray(b'\x00' * 4), 0
    if string.isascii():
        bytes_str += string.encode('utf-8')
        bytes_str += b'\x00'
        bytes_len = len(bytes_str) - 4
    else:
        bytes_str += string.encode('utf-16')[2:]
        bytes_str += b'\x00\x00'
        bytes_len = len(bytes_str) - 4
        assert bytes_len % 2 == 0
        bytes_len //= -2
    bytes_str[:4] = pack_int32(bytes_len)
    return bytes_str
    


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
            raise ParseFileError('invalid history type: {0} with cursor at 0x{1:X}'.format(self.history_type, cursor.tell()))
        
    def serialize(self):
        bytes_arr = bytearray(pack_uint32(self.flags))
        bytes_arr += pack_int8(self.history_type)
        if self.history_type == 0:
            bytes_arr += pack_string(self.namespace)
            bytes_arr += pack_string(self.key) 
            bytes_arr += pack_string(self.source_string)
        return bytes_arr
	
    def __str__(self):
        return self.source_string


class FGuid():
    def __init__(self, cursor):
        self.a = read_uint32(cursor)
        self.b = read_uint32(cursor)
        self.c = read_uint32(cursor)
        self.d = read_uint32(cursor)
        
    def serialize(self):
        bytes_arr = bytearray(pack_uint32(self.a))
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

    def __str__(self):
        return self.import_object_name
    
    def serialize(self):
        return pack_int32(self.index)

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
        self.serial_size_pos = cursor.tell()
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


class UScriptArray():
    def __init__(self, cursor, inner_type):
        self.inner_tyoe = inner_type
        self.element_count = read_uint32(cursor)
        # if inner_type in 'TextProperty' or inner_type in 'StrProperty':
        #     assert self.element_count <= 1
        self.content = []
        assert inner_type not in 'StructProperty' and inner_type not in 'ArrayProperty'
        for _ in range(self.element_count):
            if inner_type in 'BoolProperty':
                self.content.append(read_uint8(cursor) != 0)
            elif inner_type in 'ByteProperty':
                self.content.append(read_uint8(cursor))
            elif inner_type in 'ObjectProperty':
                self.content.append(FPackageIndex(cursor))
            elif inner_type in 'FloatProperty':
                raise ParseFileError('Unimplement float property reader...')
            elif inner_type in 'TextProperty':
                self.content.append(FText(cursor))
            elif inner_type in 'StrProperty':
                self.content.append(read_string(cursor))
            elif inner_type in 'NameProperty':
                name_dict = {}
                name_dict['NAME'] = read_fname(cursor, False)
                name_dict['INDEX'] = read_int32(cursor)
                self.content.append(name_dict)
            elif inner_type in 'IntProperty':
                self.content.append(read_int32(cursor))               
            elif inner_type in 'UInt16Property':
                self.content.append(read_uint16(cursor))
            elif inner_type in 'UInt32Property':
                self.content.append(read_uint32(cursor))
            elif inner_type in 'UInt64Property':
                self.content.append(read_uint64(cursor))
            # elif inner_type in 'EnumProperty': # something wrong...
            #     if tag.enum_name and tag.enum_name != 'None':
            #         self.content.append(read_fname(cursor))
            else:
                raise ParseFileError('Unknown property type...')
            
    def __str__(self):
        str_list = []
        for element in self.content:
            str_list.append(str(element))
        return '@@'.join(str_list)

    def serilize(self):
        byte_arr = bytearray(pack_uint32(self.element_count))
        inner_type = self.inner_tyoe
        if inner_type in 'BoolProperty' or inner_type in 'ByteProperty':
            for element in self.content:
                byte_arr += pack_uint8(element)
        elif inner_type in 'ObjectProperty' or inner_type in 'TextProperty':
            for element in self.content:
                byte_arr += element.serialize()
        elif inner_type in 'FloatProperty': # no float in this project...
            raise PackFileError('Unimplement float property reader...')
        elif inner_type in 'StrProperty':
            for element in self.content:
                byte_arr += pack_string(element)
        elif inner_type in 'NameProperty':
            for element in self.content:
                byte_arr += pack_fname(element['NAME'], element['INDEX'])
        elif inner_type in 'IntProperty':
            for element in self.content:
                byte_arr += pack_int32(element)             
        elif inner_type in 'UInt16Property':
            for element in self.content:
                byte_arr += pack_uint16(element)    
        elif inner_type in 'UInt32Property':
            for element in self.content:
                byte_arr += pack_uint32(element)
        elif inner_type in 'UInt64Property':
            for element in self.content:
                byte_arr += pack_uint64(element)
        else:
            raise PackFileError('Unknown property type...')
        return byte_arr
        



class FPropertyTag():
    def __init__(self, cursor, read_data: bool):
        self.name, self.val = read_fname(cursor), ''
        assert self.name
        if self.name != 'None':
            self.property_type = read_fname(cursor).strip()
            self.size = read_int32(cursor)
            self.array_index = read_int32(cursor)
            # assert self.property_type in 'TextProperty' or self.property_type in 'ObjectProperty'
            if self.property_type in 'StructProperty':
                self.struct_name = read_fname(cursor)
                self.struct_guid = FGuid(cursor)
            elif self.property_type in 'BoolProperty': # 
                self.bool_val = read_uint8(cursor) != 0
            elif self.property_type in 'EnumProperty': # 
                self.enum_name = read_fname(cursor)
            elif self.property_type in 'ByteProperty':
                self.enum_name = read_fname(cursor)
            elif self.property_type in 'ArrayProperty': #
                self.inner_type = read_fname(cursor)
            elif self.property_type in 'MapProperty':
                self.inner_type = read_fname(cursor)
                self.value_type = read_fname(cursor)
            elif self.property_type in 'SetProperty':
                self.inner_type = read_fname(cursor)         
            self.has_property_guid = read_uint8(cursor) != 0
            self.property_guid = FGuid(cursor) if self.has_property_guid else None
            cursor_pos = cursor.tell()
            if self.property_type in 'TextProperty':
                self.text_data = FText(cursor)
                # print(self.text_data.source_string)
            elif self.property_type in 'ObjectProperty': # 'ObjectProperty'
                self.object_data = FPackageIndex(cursor)
            elif self.property_type in 'EnumProperty':
                assert self.enum_name is not None
                self.enum_data = read_fname(cursor) if self.enum_name != 'None' else None
                pass
            elif self.property_type in 'ArrayProperty':
                self.array_data = UScriptArray(cursor, self.inner_type)
                pass
            final_pos = cursor_pos + self.size
            cursor.seek(final_pos, 0)
        else:
            raise ValueError('End of FPropertyTag')
    
    def __str__(self):
        if self.property_type in 'TextProperty':
            return str(self.text_data)
        elif self.property_type in 'ObjectProperty':
            return str(self.object_data)
        elif self.property_type in 'EnumProperty':
            return str(self.enum_data)
        elif self.property_type in 'ArrayProperty':
            return str(self.array_data)

    def get_name(self):
        return self.name
    
    def set_string(self, string: str):
        if self.property_type in 'TextProperty':
            self.text_data.source_string = string
            return True
        elif self.property_type in 'ArrayProperty':
            if self.array_data.element_count:
                if self.inner_type in 'TextProperty':
                    self.array_data.content[0].source_string = string
                elif self.inner_type in 'StrProperty':
                    self.array_data.content[0] = string
        return False
    
    def serialize(self):
        byte_arr = bytearray(pack_fname(self.name))
        byte_arr += pack_fname(self.property_type)

        bytes_data = b''
        if self.property_type in 'TextProperty':
            bytes_data = self.text_data.serialize()
        elif self.property_type in 'ObjectProperty':
            bytes_data = self.object_data.serialize()
        elif self.property_type in 'EnumProperty':
            if self.enum_name != 'None':
                bytes_data = pack_fname(self.enum_data)
        elif self.property_type in 'ArrayProperty':
            bytes_data = self.array_data.serilize()
        else:
            raise PackFileError('Unknown proprty type:{0}'.format(self.property_type))

        byte_arr += pack_int32(len(bytes_data))
        byte_arr += pack_int32(self.array_index)

        if self.property_type in 'EnumProperty':
            byte_arr += pack_fname(self.enum_name)
        elif self.property_type in 'ArrayProperty':
            byte_arr += pack_fname(self.inner_type)
        
        byte_arr += pack_int8(self.has_property_guid)
        if self.has_property_guid:
            byte_arr += self.property_guid.serialize()
        byte_arr += bytes_data
        return byte_arr
            

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
    
    def query(self):
        for column in self.columns:
            if column.get_name() == 'Text':
                return (self.name, self.name_num, str(column))
        return (self.name, self.name_num, '')
    
    
    def update_localization_text(self):
        global excel_dict
        if self.name in excel_dict:
            text_dict = excel_dict[self.name]
            if self.name_num in text_dict:
                string_tr = text_dict[self.name_num]
                # assert len(self.columns) == 1
                for column in self.columns:
                    if column.get_name() == 'Text' and str(column) != string_tr:
                        column.set_string(string_tr)
                        print('Update translation with name: {0}, index:{1}, content:{2}'.format(self.name, self.name_num, string_tr))

            
    def serialize(self):
        byte_arr = bytearray(pack_fname(self.name, self.name_num))
        for property_tag in self.columns:
            byte_arr += property_tag.serialize()
        byte_arr += pack_fname('None')
        return byte_arr
    

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
        self.has_serialize_guid = read_uint32(cursor)
        if self.has_serialize_guid:
            self.guid = FGuid(cursor)

    def serialize(self):
        bytes_list = []
        for property_tag in self.properties:
            bytes_list.append(property_tag.serialize())
        bytes_list.append(pack_fname('None'))
        bytes_list.append(pack_uint32(self.has_serialize_guid))
        if self.has_serialize_guid:
            bytes_list.append(self.guid.serialize())
        return b''.join(bytes_list)       
    


class UDataTable(UObject):
    def __init__(self, cursor):
        super(UDataTable, self).__init__(cursor)
        self.num_rows, self.rows = read_int32(cursor), []
        for _ in range(0, self.num_rows):
            self.rows.append(FRowStruct(cursor))
        self.checksum = read_uint32(cursor)

    def update_localization_text(self):
        for row in self.rows:
            row.update_localization_text()

    def serialize(self, test = True):
        bytes_list = []
        bytes_list.append(super().serialize())
        bytes_list.append(pack_int32(self.num_rows))
        for index, row in enumerate(self.rows):
            print('Processing: {0}/{1} ({2:.2f}%)...'.format(index, self.num_rows, float(index + 1) / self.num_rows * 100))
            bytes_list.append(row.serialize())
        bytes_list.append(pack_uint32(self.checksum))
        return b''.join(bytes_list)       

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
        """读取翻译文件"""
        for row in self.rows:
            row_name, row_name_num, row_text = row.query()
            yield row_name, row_name_num, row_text   


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


def read_localization_file(file_path):
    with open(file_path + '.uasset', 'rb') as assetFile, open(file_path + '.uexp', 'rb') as expFile:
        exp_file_length = len(expFile.read())
        expFile.seek(0, 0)
        global name_dict
        name_dict.clear()
        pack_file_summary = FPackageFileSummary(assetFile)
        assetFile.seek(pack_file_summary.name_offset, 0)
        for idx in range(pack_file_summary.name_count):
            name_dict[idx] = FNameEntrySerialized(assetFile)

        global import_dict
        import_dict.clear()
        assetFile.seek(pack_file_summary.import_offset, 0)
        for idx in range(pack_file_summary.import_count):
            import_dict[idx] = FObjectImport(assetFile)

        global export_dict
        export_dict.clear()
        assetFile.seek(pack_file_summary.export_offset, 0)
        for idx in range(pack_file_summary.export_count):
            export_dict[idx] = FObjectExport(assetFile)
            
        asset_length = pack_file_summary.total_header_size                
        for idx, export_obj in export_dict.items():
            export_type = export_obj.class_index.import_object_name
            position = export_obj.serial_offset - asset_length
            assert export_obj.serial_size == exp_file_length - 4
            expFile.seek(position, 0)
            if export_type in 'DataTable':                  
                return (export_obj.serial_size_pos, UDataTable(expFile))


def parse_excel_file(excel_dict, excel_path):
    excel_content = pd.read_excel(excel_path)
    for i in excel_content.index.values:
        row_dict = excel_content.loc[i, ['ID', 'NID', 'CN']]# .to_dict()
        row_id, row_nid, row_text = row_dict['ID'], row_dict['NID'], row_dict['CN']
        if isinstance(row_text, str):
            if row_id not in excel_dict:
                excel_dict[row_id] = {}
            excel_dict[row_id][row_nid] = row_text


def parse_localization_files_to_excel(ja_file_name, en_file_name, cn_file_name, tw_file_name, wk_file_name):
    en_data, zh_cn_data, zh_tw_data, jp_data, wk_data = {}, {}, {}, {}, {}
    _, jp_data_table = read_localization_file(SOURCE_FOLDER + ja_file_name)
    for row_id, row_num, row_text in jp_data_table:
        assert row_id not in jp_data or (row_id in jp_data and row_num not in jp_data[row_id])
        if row_id not in jp_data:
            jp_data[row_id] = {}
        jp_data[row_id][row_num] = row_text
    
    _, en_data_table = read_localization_file(SOURCE_FOLDER + en_file_name)
    for row_id, row_num, row_text in en_data_table:
        if row_id not in en_data:
            en_data[row_id] = {}
        en_data[row_id][row_num] = row_text

    _, cn_data_table = read_localization_file(SOURCE_FOLDER + cn_file_name)
    for row_id, row_num, row_text in cn_data_table:
        if row_id not in zh_cn_data:
            zh_cn_data[row_id] = {}
        zh_cn_data[row_id][row_num] = row_text
     
    _, tw_data_table = read_localization_file(SOURCE_FOLDER + tw_file_name)
    for row_id, row_num, row_text in tw_data_table:
        if row_id not in zh_tw_data:
            zh_tw_data[row_id] = {}
        zh_tw_data[row_id][row_num] = row_text
        
    _, wk_data_table = read_localization_file(SOURCE_FOLDER + wk_file_name)
    for row_id, row_num, row_text in wk_data_table:
        if row_id not in wk_data:
            wk_data[row_id] = {}
        wk_data[row_id][row_num] = row_text

    output_dict = {}
    output_dict['ID'], output_dict['NID'], output_dict['WIKI'], output_dict['CN'], output_dict['EN'], output_dict['JP'], output_dict['TW'] = [], [], [], [], [], [], []
    for row_id, row_data in zh_cn_data.items():
        for row_index, row_text in row_data.items():
            output_dict['ID'].append(row_id)
            output_dict['NID'].append(row_index)
            output_dict['WIKI'].append(wk_data[row_id][row_index] if row_id in wk_data and row_index in wk_data[row_id] else '')
            output_dict['CN'].append(row_text)
            output_dict['EN'].append(en_data[row_id][row_index] if row_id in en_data and row_index in en_data[row_id] else '')
            output_dict['JP'].append(jp_data[row_id][row_index] if row_id in jp_data and row_index in jp_data[row_id] else '')
            output_dict['TW'].append(zh_tw_data[row_id][row_index] if row_id in zh_tw_data and row_index in zh_tw_data[row_id] else '')
    
    frame_data = DataFrame.from_dict(output_dict)
    file_name_suffix = datetime.datetime.today().strftime(' %Y-%m-%d %H.%M.%S.xlsx')
    frame_data.to_excel(OUTPUT_FOLDER + cn_file_name + file_name_suffix, encoding='utf-8')

def repack_localization_files_from_excel(excel_path, cn_asset_name):
    global excel_dict
    excel_dict.clear()
    parse_excel_file(excel_dict, excel_path)
    asset_serial_pos, data_table = read_localization_file(SOURCE_FOLDER + cn_asset_name)
    if data_table is not None:
        data_table.update_localization_text()
        bytes_str = data_table.serialize()
        with open(OUTPUT_FOLDER + cn_asset_name + '.uexp', 'wb+') as outputExpFile:
            outputExpFile.write(bytes_str)
            assetFullName = cn_asset_name + '.uasset'
        with open(SOURCE_FOLDER + assetFullName, 'rb') as sourceAssetFile, open(OUTPUT_FOLDER + assetFullName, 'wb+') as outputAssetFile:
            outputAssetFile.write(sourceAssetFile.read(asset_serial_pos))
            sourceAssetFile.seek(8, 1)
            outputAssetFile.write(pack_int64(len(bytes_str) - 4))
            outputAssetFile.write(sourceAssetFile.read()) 


UNPACK_TEXT_FILE = 0
UNPACK_TALK_FILE = 1
REPACK_TEXT_FILE = 2
REPACK_TALK_FILE = 3
CURRENT_COMMAND = UNPACK_TALK_FILE

def main():
    if CURRENT_COMMAND == UNPACK_TEXT_FILE:
        parse_localization_files_to_excel(JA_TEXT_ASSET_NAME, EN_TEXT_ASSET_NAME, CN_TEXT_ASSET_NAME, TW_TEXT_ASSET_NAME, WK_TEXT_ASSET_NAME)
    elif CURRENT_COMMAND == UNPACK_TALK_FILE:
        parse_localization_files_to_excel(JA_TALK_ASSET_NAME, EN_TALK_ASSET_NAME, CN_TALK_ASSET_NAME, TW_TALK_ASSET_NAME, WK_TALK_ASSET_NAME)
    elif CURRENT_COMMAND == REPACK_TEXT_FILE:
        repack_localization_files_from_excel(TEXT_EXCEL_PATH, CN_TEXT_ASSET_NAME)
    elif CURRENT_COMMAND == REPACK_TALK_FILE:
        repack_localization_files_from_excel(TALK_EXCEL_PATH, CN_TALK_ASSET_NAME)






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
