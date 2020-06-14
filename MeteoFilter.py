import xlrd


numbers = ['44292','50527']#'30054','30089','30252','30356','30372','30374','30385','30484','30554','30565','30650','30673','30682','30695','30745','30758','30777','30823','30844','30859','30866','30879','30925','30935','30948','30949','30954','30957','30965','30968','30971','30975']
xls_files = []

for n in numbers:
    xls_files.append(xlrd.open_workbook('./Данные станций/'+n+'.xls',formatting_info=True).sheet_by_index(0))
i= 0

dates_from_file = []
dates_file = open("./Данные станций/dates.txt", "r")
for line in dates_file:
    dates_from_file.append(line.split(";")[0])

for sheet in xls_files:
    rownum = 1
    dney_s_osadkami_menee_3 = 0
    file = open('./Данные станций/'+ numbers[i] + ".txt", "a")
    i = i + 1
    while rownum < sheet.nrows:
        row = sheet.row_values(rownum)
        temp = []
        vlaga= []
        wind_power = []
        osadki = []
        data = row[0][:-6]
        #if i == 6 and data == '10.04.2020':
            #print('lol')
        if row[1] != '':
            temp.append(float(row[1]))
        if row[2] != '':
            vlaga.append(float(row[2]))
        if row[4] != '':
            wind_power.append(float(row[4]))
        if row[5] != 'Осадков нет' and row[5] != 'Следы осадков' and row[5] != '':
            osadki.append(float(row[5]))
        count = 1
        while ((rownum + count) < sheet.nrows) and (data == sheet.row_values(rownum + count)[0][:-6]):
            if sheet.row_values(rownum + count)[1] != '':
                temp.append(float(sheet.row_values(rownum + count)[1]))
            if sheet.row_values(rownum + count)[2] != '':
                vlaga.append(float(sheet.row_values(rownum + count)[2]))
            if sheet.row_values(rownum + count)[4] != '':
                wind_power.append(float(sheet.row_values(rownum + count)[4]))
            if sheet.row_values(rownum + count)[5] != 'Осадков нет' and sheet.row_values(rownum + count)[5] != 'Следы осадков' and sheet.row_values(rownum + count)[5] != '':
                osadki.append(float(sheet.row_values(rownum + count)[5]))
            count = count + 1
        rownum = rownum + count
        if len(temp) != 0:
            max_temp = round(max(temp),1)
        else:
            continue
        if len(vlaga) != 0:
            average_vlaga = round(sum(vlaga) / len(vlaga),1)
        else:
            continue
        if len(wind_power) == 0:
            average_wind_power = 0.0
        else:
            average_wind_power = round(sum(wind_power) / len(wind_power),1)
        average_osadki = sum(osadki)
        if average_osadki < 3:
            dney_s_osadkami_menee_3 = dney_s_osadkami_menee_3 +1
        else:
            dney_s_osadkami_menee_3 = 0

        if data in dates_from_file:
            file.write(data + ';' + str(max_temp)+ ';' + str(average_vlaga)+ ';' + str(average_wind_power)+ ';' + str(dney_s_osadkami_menee_3) + "\n")

    file.close()
