from src.NTFS_ADS import ADS
from src.NTFS_MFT import MFT
import argparse
import hashlib
import os
import time


def ads_func(args):
    ads = ADS()
    ads_list = ads.get_ads_list(args.filename)
    if args.list:
        for streams in ads_list:
            print(streams)
            print(ads.get_ads_content(streams))
    if args.delete:
        for streams in ads_list:
            if ads.delete_ads(streams):
                print(streams, "Delete")
            else:
                print(streams, "Error")
    if args.add:
        if args.content:
            ads.add_ads_from_stdin(args.content.encode(), args.filename, args.add)
            print("Add Finished")
        else:
            if ads.add_ads_from_file(args.filename, args.add):
                print("Add Finished")
            else:
                print("Error")
        ads_list = ads.get_ads_list(args.filename)
        for streams in ads_list:
            print(streams)
            print(ads.get_ads_content(streams))


def mft_func(args):
    mft = MFT(args.drivename)
    delete_file_list = mft.Parse_MFT()
    if args.list:
        for delete_file in delete_file_list:
            print(delete_file[1])
    if args.recover:
        lcn = None
        for delete_file in delete_file_list:
            if delete_file[1] == args.recover:
                lcn = delete_file[0]
        if lcn:
            filedata = mft.Parse_File_Data(lcn)
            target_name = time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime()) + "_" + os.path.normpath(args.recover).split(os.sep)[-1]
            with open(target_name, "wb") as f:
                f.write(filedata)
            print(target_name)
            print(hashlib.md5(filedata).hexdigest())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='数字取证技术-NTFS工具',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog='''
    隐藏数据流操作
    python .\main.py ads --filename D:\\123.txt --list
    python .\main.py ads --filename D:\\123.txt --delete
    python .\main.py ads --filename D:\\123.txt --add D:\\233.txt
    python .\main.py ads --filename D:\\123.txt --add asdf.txt --content asdfqwer
    文件恢复操作
    python .\main.py mft --drivename D: --list
    python .\main.py mft --drivename D: --recover D:\123.txt
    ''')
    subparsers = parser.add_subparsers()
    parser_ads = subparsers.add_parser('ads', help='NTFS-隐藏数据流操作')
    parser_mft = subparsers.add_parser('mft', help='NTFS-文件恢复操作')

    parser_ads.add_argument('--filename', type=str, help='文件名/路径名', required=True)
    ntfs_ads_action_exclusive_group = parser_ads.add_mutually_exclusive_group()
    ntfs_ads_action_exclusive_group.add_argument('--list', action='store_true', help='获取当前文件/文件夹中的所有隐藏数据流')
    ntfs_ads_action_exclusive_group.add_argument('--delete', action='store_true', help='删除某个隐藏数据流')
    ntfs_ads_action_exclusive_group.add_argument('--add', type=str, metavar='ADS-FILENAME', help='将内容/文件作为交换数据流写入/添加到文件或文件夹')
    parser_ads.add_argument('--content', type=str, help='待写入的内容')
    parser_ads.set_defaults(func=ads_func)

    parser_mft.add_argument('--drivename', type=str, help='驱动器名', required=True)
    ntfs_mft_action_exclusive_group = parser_mft.add_mutually_exclusive_group()
    ntfs_mft_action_exclusive_group.add_argument('--list', action='store_true', help='列出当前驱动器中处于删除状态的文件')
    ntfs_mft_action_exclusive_group.add_argument('--recover', type=str, metavar='FILENAME', help='恢复某个处于删除状态的文件并计算哈希')
    parser_mft.set_defaults(func=mft_func)

    args = parser.parse_args()
    # print(args)
    args.func(args)
