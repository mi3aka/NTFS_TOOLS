import ctypes
import os
import re

kernel = ctypes.windll.kernel32
"""
c_bool        _Bool bool (1)
c_char        char 单字符字节对象
c_wchar       wchar_t 单字符字符串
c_byte        char 整型
c_ubyte       unsigned char 整型
c_short       short 整型
c_ushort      unsigned short 整型
c_int         int 整型
c_uint        unsigned int 整型
c_long        long 整型
c_ulong       unsigned long 整型
c_longlong    __int64 或 long long 整型
c_ulonglong   unsigned __int64 或 unsigned long long 整型
c_size_t      size_t 整型
c_ssize_t     ssize_t 或 Py_ssize_t 整型
c_float       float 浮点数
c_double      double 浮点数
c_longdouble  long double 浮点数
c_char_p      char * (以 NUL 结尾) 字节串对象或 None
c_wchar_p     wchar_t * (以 NUL 结尾) 字符串或 None
c_void_p      void * int 或 None
"""
#https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-dtyp/efda8314-6e41-4837-8299-38ba0ee04b92
DWORD = ctypes.c_ulong  # typedef unsigned long DWORD, *PDWORD, *LPDWORD;
LONG = ctypes.c_long  # typedef long LONG, *PLONG, *LPLONG;
LONGLONG = ctypes.c_longlong  # typedef signed __int64 LONGLONG;
LPCWSTR = ctypes.c_wchar_p  # typedef const wchar_t* LPCWSTR;
WCHAR = ctypes.c_wchar  # typedef wchar_t WCHAR, *PWCHAR;
RULE = r":(.+?):\$DATA"  # :xxx:$DATA

#结构体和联合必须继承自 ctypes 模块中的 Structure 和 Union 。子类必须定义 _fields_ 属性


class LARGE_INTEGER_sub_struct(ctypes.Structure):
    _fields_ = [
        ("LowPart", DWORD),
        ("HighPart", LONG),
    ]


class LARGE_INTEGER(ctypes.Union):
    """
    typedef union _LARGE_INTEGER {
      struct {
        DWORD LowPart;
        LONG  HighPart;
      } DUMMYSTRUCTNAME;
      struct {
        DWORD LowPart;
        LONG  HighPart;
      } u;
      LONGLONG QuadPart;
    } LARGE_INTEGER;
    """
    _fields_ = [
        ("DUMMYSTRUCTNAME", LARGE_INTEGER_sub_struct),
        ("u", LARGE_INTEGER_sub_struct),
        ("QuadPart", LONGLONG),
    ]


class WIN32_FIND_STREAM_DATA(ctypes.Structure):
    """
    typedef struct _WIN32_FIND_STREAM_DATA {
      LARGE_INTEGER StreamSize;
      WCHAR         cStreamName[MAX_PATH + 36];
    } WIN32_FIND_STREAM_DATA, *PWIN32_FIND_STREAM_DATA;
    MAX_PATH = 260
    """
    _fields_ = [
        ("StreamSize", LARGE_INTEGER),
        ("cStreamName", WCHAR * 296),
    ]


class ADS():

    def recursive_traversal(self, filename):
        file_list = []
        if os.path.isfile(filename):
            file_list.append(filename)
        else:
            files = os.listdir(filename)
            for file in files:
                if os.path.isdir(file):
                    file_list += self.recursive_traversal(os.path.join(filename, file))
                else:
                    file_list.append(os.path.join(filename, file))
        return file_list

    def get_ads_list(self, filename):  #获取当前文件/文件夹中的所有隐藏数据流
        ads_list = []
        lpFindStreamData = WIN32_FIND_STREAM_DATA()
        kernel.FindFirstStreamW.restype = ctypes.c_void_p  #指向接收文件流数据的缓冲区的指针
        file_list = self.recursive_traversal(filename)
        for lpFileName in file_list:
            handle = ctypes.c_void_p(kernel.FindFirstStreamW(LPCWSTR(lpFileName), 0, ctypes.byref(lpFindStreamData), 0))  #返回值是一个搜索句柄
            """
            枚举指定文件或目录中具有 ::$DATA 流类型的第一个流。
            HANDLE FindFirstStreamW(
              [in]  LPCWSTR            lpFileName,
              [in]  STREAM_INFO_LEVELS InfoLevel,
              [out] LPVOID             lpFindStreamData,
                    DWORD              dwFlags
            );
            [in] lpFileName
            完全限定的文件名。
            [in] InfoLevel (保持为0即可a)
            返回数据的信息级别。此参数是 STREAM_INFO_LEVELS枚举类型中的值之一。

            [out] lpFindStreamData
            数据以 WIN32_FIND_STREAM_DATA结构返回。
            指向接收文件流数据的缓冲区的指针。此数据的格式取决于InfoLevel参数的值。
            dwFlags
            保留供将来使用。此参数必须为零。
            """
            if lpFindStreamData.StreamSize.QuadPart > 0:
                try:
                    ads_name = re.findall(RULE, lpFindStreamData.cStreamName)[0]
                except IndexError:
                    pass
                else:
                    ads_list.append("%s:%s" % (lpFileName, ads_name))
                while kernel.FindNextStreamW(handle, ctypes.byref(lpFindStreamData)):  #如果函数成功，则返回值非零。
                    """
                    BOOL FindNextStreamW(
                      [in]  HANDLE hFindStream,
                      [out] LPVOID lpFindStreamData
                    );
                    [in] hFindStream
                    先前调用 FindFirstStreamW函数返回的搜索句柄。
                    [out] lpFindStreamData
                    指向 接收有关流的信息的WIN32_FIND_STREAM_DATA结构的指针。
                    """
                    try:
                        ads_name = re.findall(RULE, lpFindStreamData.cStreamName)[0]
                    except IndexError:
                        pass
                    else:
                        ads_list.append("%s:%s" % (lpFileName, ads_name))
            kernel.FindClose(handle)  #当不再需要搜索句柄时，应使用FindClose函数将其关闭。
        return ads_list

    def get_ads_content(self, stream):  #读取某个具体的数据流
        with open(stream, "rb") as f:
            content = f.read()
        return content

    def delete_ads(self, stream):  #删除数据流
        try:
            os.remove(stream)
        except FileNotFoundError:
            return False
        else:
            return True

    def add_ads_from_stdin(self, content, original_filename, target_filename):  #将内容作为交换数据流写入到文件或文件夹 cmd echo qwer>123.txt:789.txt
        target_filename = os.path.normpath(target_filename).split(os.sep)
        filename = original_filename + ":" + target_filename[-1]
        with open(filename, "wb") as f:
            f.write(content)

    def add_ads_from_file(self, original_filename, target_filename):  #将已经存在的一个文件用交换数据流的方式添加到另外一个文件或文件夹上 cmd type 123.txt>>test:123.txt
        if os.path.exists(original_filename) and os.path.isfile(original_filename):
            with open(original_filename, "rb") as f:
                content = f.read()
            self.add_ads_from_stdin(content, original_filename, target_filename)
            return True
        else:
            return False
