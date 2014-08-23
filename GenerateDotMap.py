import png
import LatLongUTMconversion
from math import ceil, floor, sqrt
import _mysql
import colorsys


# set the following variables
# --------------------------------------------------------------


mysqlhostname = ""            # |--
mysqlusername = ""            # |  
mysqlpassword = ""            # |  set these for your particular MySQL arrangement.
mysqldatabase = ""            # |
mysqltable = "points2012pres" # |--


image_width = 2500  # output image width. height will be derived later


inverty = True # images have the (0,0) point in the top left, UTM has it in the bottom left, so you probably want this True


limitextent = False                        # False to spit out the full map, True for a subsection
topleftbound = (30.494169, -81.899422)     # | if you set limitextent to True, what bounding box do you want?
bottomrightbound = (30.136146, -81.409157) # | uses Google Maps' coordinate system (WGS84) - click a point, it'll show the coordinates
UTMZone = 17                               # what UTM zone are your coordinates in (just the number)? If you're using the Florida data included with this file, keep this at 17.


output_map_filename = "mapout.png"  # what do you want to call the map file?


# --------------------------------------------------------------
# end of variables to set





if limitextent:

    converttopleft = LatLongUTMconversion.LLtoUTM(23,topleftbound[0],topleftbound[1],UTMZone)
    convertbottomright = LatLongUTMconversion.LLtoUTM(23,bottomrightbound[0],bottomrightbound[1],UTMZone)

    maxlat = converttopleft[2]
    minlat = convertbottomright[2]
    maxlong = convertbottomright[1]
    minlong = converttopleft[1]



else:

    # find bounding box if one isn't specified
    db=_mysql.connect(mysqlhostname,mysqlusername,mysqlpassword,mysqldatabase)
    db.query("SELECT * FROM " + mysqltable + " WHERE 1 ORDER BY lat LIMIT 1")
    r=db.use_result()
    point = r.fetch_row()
    minlat = float(point[0][1])
    db.close()

    db=_mysql.connect(mysqlhostname,mysqlusername,mysqlpassword,mysqldatabase)
    db.query("SELECT * FROM " + mysqltable + " WHERE 1 ORDER BY lat DESC LIMIT 1")
    r=db.use_result()
    point = r.fetch_row()
    maxlat = float(point[0][1])
    db.close()

    db=_mysql.connect(mysqlhostname,mysqlusername,mysqlpassword,mysqldatabase)
    db.query("SELECT * FROM " + mysqltable + " WHERE 1 ORDER BY `long` LIMIT 1")
    r=db.use_result()
    point = r.fetch_row()
    minlong = float(point[0][2])
    db.close()

    db=_mysql.connect(mysqlhostname,mysqlusername,mysqlpassword,mysqldatabase)
    db.query("SELECT * FROM " + mysqltable + " WHERE 1 ORDER BY `long` DESC LIMIT 1")
    r=db.use_result()
    point = r.fetch_row()
    maxlong = float(point[0][2])
    db.close()



latdiff = maxlat - minlat
longdiff = maxlong - minlong

image_width -= 1 # adjust this to deal with counting from 0
image_height = int(ceil((image_width / longdiff) * latdiff))


# load up points, converting them to pixels in the process

pointlist = []

db=_mysql.connect(mysqlhostname,mysqlusername,mysqlpassword,mysqldatabase)
db.query("SELECT * FROM " + mysqltable + " WHERE 1 ")
r=db.use_result()
point = r.fetch_row()

while point:

    if limitextent:  # if we've set a bounding box, skip over ones outside of it

        if float(point[0][1]) < minlat or float(point[0][1]) > maxlat:
            point = r.fetch_row()
            continue
        if float(point[0][2]) < minlong or float(point[0][2]) > maxlong:
            point = r.fetch_row()
            continue

    pixellat = int(floor((float(point[0][1]) - minlat) * image_height / latdiff))

    if inverty: # deal with difference between UTM and pixel origins

        pixellat = image_height - pixellat

    pixellong = int(floor((float(point[0][2]) - minlong) * image_width / longdiff))

    pointlist.append([pixellong,pixellat,point[0][3]])

    point = r.fetch_row()

pointlist = sorted(pointlist)



# figure out pixel with highest number of points for saturation scaling

currow = -1
curcol = -1
currenthigh = 0
runninghigh = 0

for point in pointlist:

    if curcol != point[0] or currow != point[1]:

        if runninghigh > currenthigh:

            currenthigh = runninghigh

        runninghigh = 0
        curcol = point[0]
        currow = point[1]

    runninghigh += 1

maxpoints = ceil(currenthigh ** (1/3.0)) # don't want the really dense areas to overwhelm things, so knock the high end down


# alright, lets set pixel values

# all white pixels to start
outputimagematrix = []
for i in range (image_height + 1):
    outputimagematrix.append([])
    for j in range (image_width + 1):
        outputimagematrix[i].append(255)
        outputimagematrix[i].append(255)
        outputimagematrix[i].append(255)


currow = -1
curcol = -1

for point in pointlist:

    if curcol != point[0] or currow != point[1]:

        if curcol != -1:

            # I used HSV instead of RGB to calculate colors. It seemed more convenient - vary between
            # 240 and 359 for the hue to go from blue to purple to red, and move the saturation
            # to indicate how densely packed that pixel is. colorsys works between 0 and 1 for both
            # HSV and RGB, so have to convert out of it.

            pixelhue = (2.0/3.0) + (float(reppoints) / (reppoints + dempoints)) / 3.0
            pixelsat = 0.35 + (((float(reppoints + dempoints)) ** (1/3.0)) / maxpoints) * 0.65 

            if pixelhue > 1:     # just in case
                pixelhue = 1.0
            if pixelsat > 1:
                pixelsat = 1.0

            
            rgbpixel = colorsys.hsv_to_rgb(pixelhue,pixelsat,1)


            outputimagematrix[currow][curcol * 3] = int(ceil(255*rgbpixel[0]))
            outputimagematrix[currow][(curcol * 3) + 1] = int(ceil(255*rgbpixel[1]))
            outputimagematrix[currow][(curcol * 3) + 2] = int(ceil(255*rgbpixel[2]))

            

        dempoints = 0
        reppoints = 0
        curcol = point[0]
        currow = point[1]

    if point[2] == 'D':
        dempoints += 1
    if point[2] == 'R':
        reppoints += 1


png.from_array(outputimagematrix, 'RGB').save(output_map_filename)
