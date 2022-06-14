import ctypes
import os
import struct


class MFT():

    def __init__(self, path):
        if ctypes.windll.shell32.IsUserAnAdmin() == 0:  #权限检查
            print("Permission denied! Please run as Admin")
            exit(-1)
        self.Path = os.path.normpath(path).split(os.sep)
        self.NTFS_Drive = open(r"\\.\\" + self.Path[0], 'rb')  #盘符处理
        self.init()

    def init(self):
        self.NTFS_Drive.read(1)

        self.NTFS_Drive.seek(0x0b)
        self.Bytes_Per_Sec = struct.unpack('<h', self.NTFS_Drive.read(2))[0]  #扇区大小

        self.NTFS_Drive.seek(0x0d)
        self.Secs_Per_Clu = struct.unpack('<b', self.NTFS_Drive.read(1))[0]  #簇扇区数量

        self.NTFS_Drive.seek(0x30)
        self.MFT_Start_Clu = struct.unpack('<q', self.NTFS_Drive.read(8))[0]  #MFT起始簇位置

        self.MFT_Start_Posi = self.Bytes_Per_Sec * self.Secs_Per_Clu * self.MFT_Start_Clu  #MFT起始位置

    def Parse_MFT(self):  #解析$MFT文件并列出处于删除状态的MFT项
        self.NTFS_Drive.seek(self.MFT_Start_Posi)
        self.NTFS_Drive.read(56)  #读取$MFT文件头部

        ntfs_attribute_type = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
        while ntfs_attribute_type != 0x80:  #寻找80属性
            ntfs_attribute_length = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
            self.NTFS_Drive.read(ntfs_attribute_length - 8)
            ntfs_attribute_type = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
        ntfs_attribute_length = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
        self.NTFS_Drive.read(0x38)
        runlist = self.NTFS_Drive.read(ntfs_attribute_length - 0x40)
        runList_lowPart_length = runlist[0] % 16
        runList_low_part = int.from_bytes(runlist[1:runList_lowPart_length + 1], "little")  #$MFT文件占用簇数量
        secs = runList_low_part * self.Secs_Per_Clu  #$MFT文件占用扇区数量
        delete_file_list = []

        for sec in range(secs):
            seek_posi = self.MFT_Start_Posi + sec * self.Bytes_Per_Sec
            self.NTFS_Drive.seek(seek_posi)
            mft_data = self.NTFS_Drive.read(self.Bytes_Per_Sec)
            if mft_data[:4] == b"FILE" and struct.unpack('<h', mft_data[0x16:0x18])[0] == 0:
                delete_file_list.append([seek_posi])

        del mft_data

        for item in delete_file_list:
            full_filename = self.Find_Full_Filename(item[0])
            item.append(full_filename)
        return delete_file_list

    def Find_Full_Filename(self, mft_lcn):
        if mft_lcn == self.MFT_Start_Posi + 0x1400:  #根目录位于MFT表的第五个记录,相对MFT偏移为0x1400
            return self.Path[0]
        self.NTFS_Drive.seek(mft_lcn)
        self.NTFS_Drive.read(56)  #读取MFT头部

        ntfs_attribute_type = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
        while ntfs_attribute_type != 0x30:  #寻找30属性
            ntfs_attribute_length = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
            self.NTFS_Drive.read(ntfs_attribute_length - 8)
            ntfs_attribute_type = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
        ntfs_attribute_length = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
        self.NTFS_Drive.read(0x10)
        ntfs_attribute_detail = self.NTFS_Drive.read(ntfs_attribute_length - 0x18)

        parent_file_mft = struct.unpack('<l', ntfs_attribute_detail[:4])[0]
        parent_file_mft_lcn = self.MFT_Start_Posi + parent_file_mft * self.Bytes_Per_Sec * 2
        filename = ntfs_attribute_detail[0x42:0x42 + ntfs_attribute_detail[0x40] * 2].decode('utf-16')  #ntfs_attribute_detail[0x40] 文件名长度
        return "%s\%s" % (self.Find_Full_Filename(parent_file_mft_lcn), filename)

    def Parse_INDX(self, filename, mft_lcn=False):
        if mft_lcn:
            self.NTFS_Drive.seek(mft_lcn)
            self.NTFS_Drive.read(56)  #读取MFT头部

            ntfs_attribute_type = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
            while ntfs_attribute_type != 0x90:  #寻找90属性
                ntfs_attribute_length = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
                self.NTFS_Drive.read(ntfs_attribute_length - 8)
                ntfs_attribute_type = struct.unpack('<l', self.NTFS_Drive.read(4))[0]

            self.NTFS_Drive.read(12)
            stream_size = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
            stream_offset = struct.unpack('<h', self.NTFS_Drive.read(2))[0]
            self.NTFS_Drive.read(stream_offset - 16 - 6 + 0x20)  #部分属性头以及索引根与索引头
            stream_already_read_size = 0x20
        else:
            self.NTFS_Drive.seek(self.INDEX_Allocation_Attr)
            self.NTFS_Drive.read(56)  #读取MFT头部

            ntfs_attribute_type = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
            while ntfs_attribute_type != 0xA0:  #寻找根目录项中的A0属性
                ntfs_attribute_length = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
                self.NTFS_Drive.read(ntfs_attribute_length - 8)
                ntfs_attribute_type = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
            ntfs_attribute_length = struct.unpack('<l', self.NTFS_Drive.read(4))[0]

            index_allocation_runList = self.NTFS_Drive.read(ntfs_attribute_length - 8)[-8:]  #读取RunList
            runList_highPart_length = index_allocation_runList[0] // 16
            runList_lowPart_length = index_allocation_runList[0] % 16
            # runList_low_part = int.from_bytes(index_allocation_runList[1:runList_lowPart_length + 1], "little")  #簇大小
            runList_high_part = int.from_bytes(index_allocation_runList[runList_lowPart_length + 1:runList_highPart_length + runList_lowPart_length + 1], "little")  #起始簇位置
            root_indx_attr = runList_high_part * self.Bytes_Per_Sec * self.Secs_Per_Clu  #根目录INDX索引区域位置
            # self.INDX_Size = runList_low_part * self.Bytes_Per_Sec * self.Secs_Per_Clu  #根目录INDX索引区域大小

            self.NTFS_Drive.seek(root_indx_attr)
            indx_header = self.NTFS_Drive.read(0x20)  #读取根目录INDX索引头
            stream_size = struct.unpack('<l', indx_header[0x1c:0x20])[0]
            stream_offset = struct.unpack('<h', indx_header[0x18:0x1a])[0]  #解析根目录INDX索引项偏移
            self.NTFS_Drive.read(stream_offset - 8)
            stream_already_read_size = 0x20 + stream_offset - 8

        index_item_mft_lcn = -1
        while True:
            index_stream_pre_16bytes = self.NTFS_Drive.read(0x10)  #读取索引项的前16字节
            index_stream_length = struct.unpack('<h', index_stream_pre_16bytes[0x08:0x0a])[0]
            index_stream_detail = self.NTFS_Drive.read(index_stream_length - 0x10)
            index_filename_length = struct.unpack('<b', index_stream_detail[0x50 - 0x10:0x51 - 0x10])[0] * 2
            index_filename = index_stream_detail[0x52 - 0x10:0x52 - 0x10 + index_filename_length].decode('utf-16')
            stream_already_read_size += index_stream_length
            if filename == index_filename:
                index_item_mft = struct.unpack('<l', index_stream_pre_16bytes[0x00:0x04])[0]  #解析当前索引项的MFT位置
                index_item_mft_lcn = self.MFT_Start_Posi + index_item_mft * self.Bytes_Per_Sec * 2  #解析该MFT所在的逻辑簇
                break
            if stream_size - stream_already_read_size <= 0x10:
                break
        return index_item_mft_lcn

    def Parse_File_Data(self, mft_lcn):
        self.NTFS_Drive.seek(mft_lcn)
        self.NTFS_Drive.read(56)  #读取MFT头部

        ntfs_attribute_type = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
        while ntfs_attribute_type != 0x80:  #寻找80属性
            ntfs_attribute_length = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
            self.NTFS_Drive.read(ntfs_attribute_length - 8)
            ntfs_attribute_type = struct.unpack('<l', self.NTFS_Drive.read(4))[0]

        ntfs_attribute_length = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
        NTFSAttribute = self.NTFS_Drive.read(8)
        NonResidentFiag = NTFSAttribute[0]
        if NonResidentFiag == 1:  #非常驻属性
            self.NTFS_Drive.read(0x30)  #CNonResident
            runList = self.NTFS_Drive.read(ntfs_attribute_length - 0x40)
            runList_index = 0
            runList_low_part = []
            runList_high_part = []
            runList_start = runList[runList_index]
            while runList_start != 0:
                runList_high_part_length = runList_start // 16
                runList_low_part_length = runList_start % 16
                runList_index += 1
                runList_low_part.append(int.from_bytes(runList[runList_index:runList_low_part_length + runList_index], "little"))
                runList_high_part.append(int.from_bytes(runList[runList_low_part_length + runList_index:runList_high_part_length + runList_low_part_length + runList_index], "little", signed=True))
                runList_index = runList_high_part_length + runList_low_part_length + runList_index
                if runList_index >= ntfs_attribute_length - 0x40:
                    break
                runList_start = runList[runList_index]
            File_detail_Attr = runList_high_part[0] * self.Bytes_Per_Sec * self.Secs_Per_Clu
            self.NTFS_Drive.seek(File_detail_Attr)
            print(File_detail_Attr)
            print(self.NTFS_Drive.read(runList_low_part[0] * self.Bytes_Per_Sec * self.Secs_Per_Clu).decode('utf-16'))
        else:
            cresident = self.NTFS_Drive.read(8)
            stream_size = struct.unpack('<l', cresident[0:4])[0]
            stream_offset = struct.unpack('<h', cresident[4:6])[0]
            self.NTFS_Drive.read(stream_offset - 0x18)
            filedata = self.NTFS_Drive.read(stream_size)
            return filedata
