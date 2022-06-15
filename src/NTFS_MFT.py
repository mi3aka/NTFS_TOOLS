import ctypes
import os
import struct
"""
https://www.jianshu.com/p/8471b7f4152a
typedef struct NTFS_BPB{//fsutil fsinfo ntfsinfo d: 查询 NTFS 信息
    UCHAR jmpCmd[3];
    UCHAR s_ntfs[8];            // "NTFS" 标志
    // 0x0B
    UCHAR bytesPerSec[2];       //  0x0200  扇区大小512B
    UCHAR SecsPerClu;           //  0x08    每簇扇区数4KB
    UCHAR rsvSecs[2];           //  保留扇区
    UCHAR noUse01[5];           //
    // 0x15
    UCHAR driveDscrp;           //  0xF8 磁盘介质 -- 硬盘
    UCHAR noUse02[2];           //
    // 0x18
    UCHAR SecsPerTrack[2];      // 0x003F   每道扇区数 63
    UCHAR Headers[2];           // 0x00FF   磁头数
    UCHAR secsHide[4];          // 0x3F     隐藏扇区
    UCHAR noUse03[8];           //
    // 0x28
    UCHAR allSecsNum[8];        // 卷总扇区数, 高位在前, 低位在后
    // 0x30
    UCHAR MFT_startClu[8];      // MFT 起始簇
    UCHAR MFTMirr_startClu[8];  // MTF 备份 MFTMirr 位置
    //0x40
    UCHAR cluPerMFT[4];         // 每记录簇数 0xF6
    UCHAR cluPerIdx[4];         // 每索引簇数
    //0x48
    UCHAR SerialNum[8];         // 卷序列号
    UCHAR checkSum[8];          // 校验和
}Ntfs_Bpb,*pNtfs_Bpb;


typedef struct MFT_HEADER{          // 共56字节
    UCHAR    mark[4];               // "FILE" 标志 
    UCHAR    UsnOffset[2];          // 更新序列号偏移 30 00
    UCHAR    usnSize[2];            // 更新序列数组大小+1 03 00
    UCHAR    LSN[8];                // 日志文件序列号(每次记录修改后改变) 58 8E 0F 34 00 00 00 00
    // 0x10
    UCHAR    SN[2];                 // 序列号 随主文件表记录重用次数而增加
    UCHAR    linkNum[2];            // 硬连接数 (多少目录指向该文件) 01 00
    UCHAR    firstAttr[2];          // 第一个属性的偏移 38 00
    UCHAR    flags[2];              // 0已删除 1正常文件 2已删除目录 3目录正使用
    // 0x18
    UCHAR    MftUseLen[4];          // 记录有效长度   A8 01 00 00
    UCHAR    maxLen[4];             // 记录占用长度  00 04 00 00
    // 0x20
    UCHAR    baseRecordNum[8];      // 索引基本记录, 如果是基本记录则为0
    UCHAR    nextAttrId[2];         // 下一属性Id07 00
    UCHAR    border[2];
    UCHAR    xpRecordNum[4];        // 用于xp, 记录号
    // 0x30
    UCHAR    USN[8];                // 更新序列号(2B) 和 更新序列数组
}Mft_Header, *pMft_Header;

//------------------  属性头通用结构 ----
//非常驻属性,属性头大小为64字节
//常驻属性,属性头大小为24字节
//常驻属性是直接保存再MFT中,非常驻属性保存再MFT之外的其他地方
//如果文件或文件夹小于1500字节,那么它们的所有属性,包括内容都会常驻在MFT中
typedef struct NTFSAttribute //所有偏移量均为相对于属性类型 Type 的偏移量
{
    UCHAR Type[4];              // 属性类型 0x10, 0x20, 0x30, 0x40,...,0xF0,0x100
                                // A0H表示索引分配属性,记录根目录中所有文件的文件名以及文件记录的位置
    UCHAR Length[4];            // 属性的长度 
    UCHAR NonResidentFiag;      // 是否是非常驻属性,l 为非常驻属性,0 为常驻属性 00
    UCHAR NameLength;           // 属性名称长度,如果无属性名称,该值为 00
    UCHAR ContentOffset[2];     // 属性内容的偏移量  18 00
    UCHAR CompressedFiag[2];    // 该文件记录表示的文件数据是否被压缩过 00 00
    UCHAR Identify[2];          // 识别标志  00 00
//--- 0ffset: 0x10 ---
//--------  常驻属性和非常驻属性的公共部分 ----
    union CCommon
    {
        //---- 如果该属性为 常驻 属性时使用该结构 ----
        struct CResident
        {
            UCHAR StreamLength[4];          // 属性值的长度, 即属性具体内容的长度。"48 00 00 00"
            UCHAR StreamOffset[2];          // 属性值起始偏移量  "18 00"
            UCHAR IndexFiag[2];             // 属性是否被索引项所索引,索引项是一个索引(如目录)的基本组成  00 00
        };
        //------- 如果该属性为 非常驻 属性时使用该结构 ----
        struct CNonResident
        {
            UCHAR StartVCN[8];              // 起始的 VCN 值(虚拟簇号：在一个文件中的内部簇编号,0起
            UCHAR LastVCN[8];               // 最后的 VCN 值
            UCHAR RunListOffset[2];         // 运行列表的偏移量
            UCHAR CompressEngineIndex[2];   // 压缩引擎的索引值,指压缩时使用的具体引擎。
            UCHAR Reserved[4];
            UCHAR StreamAiiocSize[8];       // 为属性值分配的空间,单位为B,压缩文件分配值小于实际值
            UCHAR StreamRealSize[8];        // 属性值实际使用的空间,单位为B
            UCHAR StreamCompressedSize[8];  // 属性值经过压缩后的大小, 如未压缩, 其值为实际值
        };
    };
};
"""


class MFT():

    def __init__(self, path):
        if ctypes.windll.shell32.IsUserAnAdmin() == 0:  #权限检查
            print("Permission denied! Please run as Admin")
            exit(-1)
        self.drivename = os.path.normpath(path).split(os.sep)[0]
        self.NTFS_Drive = open(r"\\.\\" + self.drivename, 'rb')  #盘符处理
        self.init()

    def __del__(self):
        self.NTFS_Drive.close()

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
            return self.drivename
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

    def Parse_File_Data(self, mft_lcn):
        self.NTFS_Drive.seek(mft_lcn)
        self.NTFS_Drive.read(56)  #读取MFT头部

        ntfs_attribute_type = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
        while ntfs_attribute_type != 0x80:  #寻找80属性
            ntfs_attribute_length = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
            self.NTFS_Drive.read(ntfs_attribute_length - 8)
            ntfs_attribute_type = struct.unpack('<l', self.NTFS_Drive.read(4))[0]

        ntfs_attribute_length = struct.unpack('<l', self.NTFS_Drive.read(4))[0]
        ntfs_attribute = self.NTFS_Drive.read(8)
        non_resident_property = ntfs_attribute[0]
        if non_resident_property == 1:  #非常驻属性
            cnonresident = self.NTFS_Drive.read(0x30)  #CNonResident
            stream_real_size = struct.unpack('<q', cnonresident[0x20:0x28])[0]
            runlist = self.NTFS_Drive.read(ntfs_attribute_length - 0x40)
            runlist_index = 0
            runlist_low_part = []
            runlist_high_part = []
            runlist_start = runlist[runlist_index]
            while runlist_start != 0:
                runlist_high_part_length = runlist_start // 16
                runlist_low_part_length = runlist_start % 16
                runlist_index += 1
                runlist_low_part.append(int.from_bytes(runlist[runlist_index:runlist_low_part_length + runlist_index], "little"))
                runlist_high_part.append(int.from_bytes(runlist[runlist_low_part_length + runlist_index:runlist_high_part_length + runlist_low_part_length + runlist_index], "little", signed=True))
                runlist_index = runlist_high_part_length + runlist_low_part_length + runlist_index
                if runlist_index >= ntfs_attribute_length - 0x40:
                    break
                runlist_start = runlist[runlist_index]
            file_data = b""
            for i in range(0, len(runlist_high_part) - 1):
                file_detail_attr = runlist_high_part[i] * self.Bytes_Per_Sec * self.Secs_Per_Clu
                self.NTFS_Drive.seek(file_detail_attr)
                file_data += self.NTFS_Drive.read(runlist_low_part[i] * self.Bytes_Per_Sec * self.Secs_Per_Clu)
                stream_real_size -= runlist_low_part[i] * self.Bytes_Per_Sec * self.Secs_Per_Clu
            file_detail_attr = runlist_high_part[len(runlist_high_part) - 1] * self.Bytes_Per_Sec * self.Secs_Per_Clu
            self.NTFS_Drive.seek(file_detail_attr)
            file_data += self.NTFS_Drive.read(stream_real_size)
            return file_data
        else:
            cresident = self.NTFS_Drive.read(8)
            stream_size = struct.unpack('<l', cresident[0:4])[0]
            stream_offset = struct.unpack('<h', cresident[4:6])[0]
            self.NTFS_Drive.read(stream_offset - 0x18)
            file_data = self.NTFS_Drive.read(stream_size)
            return file_data
