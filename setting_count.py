import pickle


def create_setting_file(directory, product_name,
                        matching_threshold=None, erode_size=None, dilate_size=None, thresh_area=None,
                        h_range=None, l_range=None, s_range=None):
    """
    設定ファイルを作成する関数
    :param directory:
    :param product_name:
    :param matching_threshold:
    :param erode_size:
    :param dilate_size:
    :param thresh_area:
    :param h_range:
    :param l_range:
    :param s_range:
    :return:
    """
    if matching_threshold is None:
        matching_threshold = 0.85
    if erode_size is None:
        erode_size = 5
    if dilate_size is None:
        dilate_size = 3
    if thresh_area is None:
        thresh_area = 100
    if h_range is None:
        h_range = 180
    if l_range is None:
        l_range = 255
    if s_range is None:
        s_range = 255
    filename = directory + product_name + ".pkl"
    data = {"matching_threshold": matching_threshold,
            "erode_size": erode_size,
            "dilate_size": dilate_size,
            "thresh_area": thresh_area,
            "h_range": h_range,
            "l_range": l_range,
            "s_range": s_range}
    with open(filename, "wb") as f:
        pickle.dump(data, f)


def load_setting_file(directory, product_name):
    """
    設定ファイルから設定値を読み込む
    :param directory:
    :param product_name:
    :return:
    """
    filename = directory + product_name + ".pkl"
    with open(filename, "rb") as f:
        data = pickle.load(f)

    matching_threshold = data["matching_threshold"]
    erode_size = data["erode_size"]
    dilate_size = data["dilate_size"]
    thresh_area = data["thresh_area"]
    h_range = data["h_range"]
    l_range = data["l_range"]
    s_range = data["s_range"]
    return matching_threshold, erode_size, dilate_size, thresh_area, h_range, l_range, s_range
