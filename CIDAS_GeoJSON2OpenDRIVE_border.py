from matplotlib.pyplot import axis
import numpy as np


def cal_bcd(a, s1, s2, s3, dis1, dis2, dis3):
    # AX=B,x=[b c d]
    #X = np.array([[s1,s2,s3],[s1**2,s2**2,s3**2],[s1**3,s2**3,s3**3]])
    A = np.array([[s1, s1**2, s1**3], [s2, s2**2, s2**3],
                 [s3, s3**2, s3**3]]).reshape((3, 3))
    s = np.array([s1, s2, s3])
    B = np.array([dis1-a, dis2-a, dis3-a]).reshape(3, 1)
    print(A, B)
    A_inv = np.linalg.inv(A)
    X = A_inv*B
    print('X', X)
    # X1 = np.linalg.inv(A.T*A)*(A.T*B)
    # print('x1',X1)
    X_final = X.insert(0, a)
    return X_final


def cut(line, count):
    # Cuts a line in two at a distance from its starting point
    distance = line.length/count
    # if distance <= 0.0 or distance >= line.length:
    #     return [LineString(line)]

    coords = list(line.coords)
    cut_point = [coords[0]]
    cut_len = [0]
    sum_dis = 0
    for i, p in enumerate(coords):
        pd = line.project(Point(p))
        if pd == distance:
            return [LineString(coords[:i+1]), LineString(coords[i:])]
        if pd > distance:
            for j in range(1, count, 1):
                cp = line.interpolate(distance*j)
                cut_point.append((cp.x, cp.y))
                sum_dis += distance
                cut_len.append(sum_dis)
            # return [LineString(coords[:i] + [(cp.x, cp.y)]),LineString([(cp.x, cp.y)] + coords[i:])]
            cut_point.append(coords[-1])
            cut_len.append(line.length)
            return cut_point, cut_len


def write_xodr(xmlpath, shppath, savepath):
    # 读取rnd_master文件
    tree = ET.parse(xmlpath)
    root = tree.getroot()

    # 读取shapefile文件
    lines_raw = geopandas.read_file(shppath)
    lines = lines_raw[lines_raw['track'] != str('0')].reset_index(drop=True)
    track_group = lines['track'].unique()
    for t in track_group:
        track_lines = lines[lines['track'] == str(t)].reset_index(drop=True)
        lines_group = track_lines['laneid'].unique()
        l_group = sorted([float(i) for i in lines_group],
                         reverse=True)  # 按laneid升序排列

        # 先写road
        track = track_lines[track_lines['laneid'] ==
                            str('0')].reset_index(drop=True).geometry[0]
        # print(track.length,len(track.coords),list(track.coords))
        # print(list(track.coords)[0],type(list(track.coords)[0][0]))

        road_attrib = {"id": str(t), "junction": "-1",
                       "length": str(track.length), "name": ""}
        road = ET.SubElement(root, 'road', road_attrib)
        road_link = ET.SubElement(road, 'link', {})
        # planView
        road_planView = ET.SubElement(road, 'planView', {})
        # lane section
        road_lanes = ET.SubElement(road, 'lanes', {})
        sum_track_len = 0
        track_len = [0]
        for i in range(len(track.coords) - 1):
            sx, sy = list(track.coords)[i][:]
            ex, ey = list(track.coords)[i+1][:]
            length, heading = cal_length_angle_CCW(sx, sy, ex, ey)
            road_planView = write_road_geom(road_planView, math.radians(
                heading), length, sum_track_len, sx, sy)
            sum_track_len += length
            track_len.append(sum_track_len)

        #print((track_lines[track_lines['laneid'] == str(int(-1.0))].geometry[0]))

        lane_dict = {}
        for j in l_group:
            lane_temp = track_lines[track_lines['laneid'] == str(
                int(j))].reset_index(drop=True).geometry[0]
            lane_dict[j] = lane_temp

        for i in range(len(track.coords)-1):
            # sx, sy = list(track.coords)[i][:]
            # p = geopandas.GeoSeries(Point(sx,sy))
            # p.crs = 32651

            line_i = LineString(track.coords[i:i+2])
            cut_point_list, cut_len_list = cut(line_i, 3)  # 第一个为起点，计算a，最后一个为终点
            print(cut_len_list)

            lanesection_attrib = {"s": "0"}
            lanesection_attrib["s"] = str(track_len[i])
            lanes_lanesection = ET.SubElement(
                road_lanes, 'laneSection', lanesection_attrib)
            ls_left = ET.SubElement(lanes_lanesection, 'left', {})
            ls_center = ET.SubElement(lanes_lanesection, 'center', {})
            ls_right = ET.SubElement(lanes_lanesection, 'right', {})

            lane_dis = []
            for k in range(len(l_group)):
                lane = lane_dict[l_group[k]]
                lane_dis = []
                if k != 0:
                    for c in range(len(cut_len_list)):
                        p = geopandas.GeoSeries(Point(cut_point_list[c]))
                        p.crs = 32651
                        p_s = cut_len_list[c]
                        p_dis = list(p.distance(lane))[0]
                        lane_dis.append(p_dis)
                    print(k, lane_dis)
                    abcd = cal_bcd(lane_dis[0], cut_len_list[1], cut_len_list[2],
                                   cut_len_list[3], lane_dis[1], lane_dis[2], lane_dis[3])
                    print(abcd)

            zero_index = lane_dis.index(0)
            lane_dis_relative = [abs(lane_dis[i+1]-lane_dis[i])
                                 for i in range(len(lane_dis)-1)]
            lane_dis_relative.insert(zero_index, 0)
            for k in range(len(l_group)):
                lanes_lanesection = write_lane(
                    lanes_lanesection, ls_left, ls_center, ls_right, laneid=l_group[k], a=lane_dis_relative[k], b=0)

    pretty_xml(root, '\t', '\n')
    tree.write(savepath, encoding='utf-8', xml_declaration=True)
    print('\n成功保存文件：', savepath)


if __name__ == '__main__':
    # root = tk.Tk()
    # root.withdraw()
    # master_path = r'D:\Prj_CIDAS_PCM_CATRC\CIDAS_lyq\5223180115\TEST\CIDAS_Master.xodr'
    # # jsonpath = r'D:\Prj_CIDAS_PCM_CATRC\CIDAS_lyq\5223180115\TEST\5223180115_Manualz.shp'
    # # savepath = r'D:\Prj_CIDAS_PCM_CATRC\CIDAS_lyq\5223180115\TEST\5223180115_Manual_shp.xodr'
    # jsonpath = filedialog.askopenfilename(title=u'经过手工调整的shapefile文件，局部坐标',filetypes=[("ERSI Shapefile文件", "*.shp")])
    # savepath = filedialog.asksaveasfilename(title=u'xodr保存路径及名字',filetypes=[("OpenDRIVE文件", "*.xodr")])
    # rnd_origin = [float(273981.232094992), float(3479507.72561738), float(0)]
    # # filename,coord_dict = read_geojson(jsonpath,rnd_origin)
    # # print(filename,coord_dict)
    # # Get_xodr(master_path,coord_dict,savepath)
    # write_xodr(master_path,jsonpath,savepath)
    s = np.array(
        [9.127888901757899, 18.255777803515798, 27.383666705273697]).reshape((3, 1))
    A = np.concatenate([s, s**2, s**3], axis=1)

    dis = np.array([3.366499865198679, 3.3575975572331602,
                    3.300126244349445]).reshape((3, 1))
    print(A.shape)
    A_inv = np.linalg.inv(A)
    print(np.matmul(A_inv, dis))

    # a = 3.395537374780044
