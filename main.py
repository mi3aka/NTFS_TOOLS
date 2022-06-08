from src.NTFS_ADS import ADS

filename = "."
ads = ADS()
ads_list = ads.get_ads_list(filename)
if len(ads_list):
    for streams in ads_list:
        print(streams)
        print(ads.get_ads_content(streams))
