#!/usr/bin/env python
# coding: utf-8

import datetime
import pandas as pd
import gpxpy as gpxpy
import numpy as numpy

#Setting up inputs
print('To use this script, pandas, numpy, and gpxpy must be installed / in evironment')

# Path to GPX file
gpx_fpath = input('Enter the path to the .gpx file you have:') #File Path
print('Thanks! Reading your file and doing some processing. This may take awhile depending on the size of the file.') #user heads up

#Show where GPXPy will take the file from.
with open(gpx_fpath) as gpxf:
    gpxparse = gpxpy.parse(gpxf) #Parse the file when called.

#Setup
points= [] #Sets up a list to store records for points to be converted int a dataframe.
trk_ct = 0 #Keeps track of number of tracks
trk_reset = 0 # Track Reset helps keep count of the track segment count by putting at end of track run.
trkseg_tot = 0 #Keeps track of total number of segments
trkseg_ct = 0 #Keeps track of number of track segments in current track

# Take the parsed file and make a memory object from contents
for track in gpxparse.tracks: #Itterate through the Tracks
    trk_ct = trk_ct + 1 #Add up Tracks
    
    for segment in track.segments: #Ittertate through the track segments within the tracks
        trkseg_tot = trkseg_tot + 1 #Add to the total number of tracks
        if trk_ct > trk_reset: # If trk_count > Track Reset, then a new track has been processed!
            trkseg_ct = 0 #Reset track segment count.
        else: #If not, pass through.
            pass
        trkseg_ct = trkseg_ct + 1 #Itterate through the current track segments.
        
        for pts in segment.points: #For the points in the segments
            points.append({ #Append to the list
            'time': pts.time, #In collumn Time, add record time
            'latitude': pts.latitude, #In collumn latitude, add record latitude
            'longitude': pts.longitude, #In collumn longitude, add record longitude
            'speedmph': round((pts.speed * 2.236936),1), #In collumn speed, add record speed
            'elevationft': round((pts.elevation * 3.28084),0), #In collumn elevation, add record elevation
            'gpxsegid': str(trk_ct) +'-'+ str(trkseg_ct) #Make an track/segment ID with the trackers.
            }) 
            
    trk_reset = trk_reset + 1 #Variable for also keeping tabs on # of tracks run, this time at the end.

#Make a pandas dataframe from the points list and call it df
df = pd.DataFrame.from_records(points)

#Make sure time is in UTC
df['time'] = pd.to_datetime(df['time']).dt.tz_convert('UTC')

#Use the time to create a time delta collumn
df['gpxtd'] = pd.to_timedelta(df['time'].diff(+1),unit ='s') #Creates a time delta collumn
df['gpxtd'] = df['gpxtd'] / pd.Timedelta(seconds=1) #Turns it into a float with number of seconds.
df = df.drop(df[df.gpxtd == 0].index) #Dropping rows in DF where TD = 0
df['gpxtd'] = df['gpxtd'].fillna(0) #If we have a 'NaN', convert it to zero
df.reset_index(drop=True, inplace=True) #We Reset the index numbering so we can itterate through it in next section.

#Direction / Heading of Travel calculation
def _CalcBearing_(latA,lonA,latB,lonB):
    dLon = lonB - lonA
    x = numpy.cos(numpy.radians(latB)) * numpy.sin(numpy.radians(dLon))
    y = numpy.cos(numpy.radians(latA)) * numpy.sin(numpy.radians(latB)) - numpy.sin(numpy.radians(latA)) * numpy.cos(numpy.radians(latB)) * numpy.cos(numpy.radians(dLon))                                               
    bearing = numpy.arctan2(x, y)
    bearing = numpy.degrees(bearing)
    #if bearing < 0: bearing += 360 #We do this later when pandas isn't a bitch about series type.
    return bearing

#Make a new dataframe collumn and calculate the heading
df['heading'] = _CalcBearing_(df['latitude'],df['longitude'],df['latitude'].shift(-1), df['longitude'].shift(-1))
df['heading'] = df['heading'].fillna(0) #If we have a 'NaN', convert it to zero
df['heading'] = df['heading'].apply(lambda x: x+360 if x< 0 else x) #now we make the correction
df['heading'] = df['heading'].apply(lambda x: round(x, 1)) #round it off.

#Done with setting up datatable!
#Now informing and getting info from the user.
print('This .gpx file consists of '+str(trk_ct)+' tracks, '+ str(trkseg_tot)+' track segments, and '+ str(len(df.index))+ ' points.')
pfilename = input('What do you want your placefile to be called?') #File output name
spottername = input('Type in the SN Dot Label you want, ex. Name, Callsign, Team, etc.')
timediv = int(input('Enter number of seconds you want between placefile location updates in seconds, between 60 and 300 is recommended.'))
print('Processing....') #user heads up


#We have to create a new pandas dataframe to pull from., Setting up some variables for the next section
elapsetrack = 0 #This tracks how much time has passed in the time delta.
processnum = 0  #This is our processing locations counter.
placepts = [0,] #This creates a list and we want the 1st point and last point included as default.

#Finding the indexes that are x seconds apart.
for index in range(len(df.index)): #Itterate through the list
    if elapsetrack < timediv: #Activate if elaspetrack is less than timdiv
        elapsetrack = elapsetrack + int(df.loc[index,'gpxtd']) #Add number of seconds to elapsetrack
        continue #Go back to top of if statement
    else:
        elapsetrack = int(df.loc[index,'gpxtd']) #Reset elapsetrack back to td of last rec taken.
        placepts.append(index) #Append to the list
        continue #Go back to top of if statement
        
placepts.sort() #Sorts the list by number order.
#print(placepts)
dfp = df.loc[placepts] #Makes a new dataframe using the list of records we just created.
dfp.reset_index(inplace=True) #We Reset the index numbering so we can itterate through it in next section.

#Setting up outputs
with open(str(pfilename)+".txt", "a") as fout: #Write a new file
 
    #Placefile Header
    fout.write(
        ';This placefile was generated by a python script by James Hyde (wxmeddler@gmail.com), '+
        'originally found at https://github.com/wxmeddler/ \n' +
        'Refresh: 60\n' + 
        'Threshold: 999\n' + 
        'Title:'+ str(pfilename) +'\n' +
        'Font: 1, 11, 0,"Courier New"\n'+
        'IconFile: 1, 22, 22, 11, 11, "http://www.spotternetwork.org/icon/spotternet_new.png"\n' +
        'IconFile: 2, 15, 25, 8, 25, "http://www.spotternetwork.org/icon/arrows.png"\n\n')

    #Itterate through new dataframe to generate locations
    for index in range(len(dfp.index)): #Itterate over all the rows in the dataframe
        
        #TimeStuff
        currdt = dfp.loc[index,'time'] #Take DateTime from the dataframe
    
        try: #This handles taking the next time
            nextdt = dfp.loc[index+1,'time'] #Take the next row's DateTime from CSV
        except: #and what happens if there is no next row
            nextdt = currdt + datetime.timedelta(minutes=5) #make the next time the current report time plus 5 min.
          
        #This is a safety catch; if somehow the two times are the same, add another second.  
        if currdt == nextdt:
            nextdt = nextdt + datetime.timedelta(seconds = 1)
    
        #Object Lat/Lon ; takes and prints the current index / row lat and lon.
        fout.write('Object: '+ str(dfp.loc[index,'latitude']) + ',' + str(dfp.loc[index,'longitude'])+'\n')
    
        #Timerange ; Spits out the time and next time in iso format
        fout.write('Timerange: '+ str(currdt.strftime('%Y-%m-%dT%H:%M:%SZ '))+ str(nextdt.strftime('%Y-%m-%dT%H:%M:%SZ'))+'\n')
    
        #If moving less than 1 mph, then don't need direction arrow.
        if dfp.loc[index,'speedmph'] < 1:
            pass #if we're going near zero mph, pass down to next section
        else: #If there is a speed, assign a direction arrow.
            fout.write('Icon: 0,0,'+ str(round(dfp.loc[index,'heading'],1)) +',2,15,'+'\n')
            pass 
        
       #Hover Over Icon Text
        fout.write('Icon: 0,0,000,1,2,"'+ str(spottername) + '\\n'+
                   'Position Time: '+ str(str(currdt.strftime('%Y-%m-%d %H:%M:%SZ')) +'\\n'+
                    'Heading: '+ str(dfp.loc[index,'heading']) +' deg.\\n'
                    'Speed: '+ str(dfp.loc[index,'speedmph'])) +' mph\\n'
                   'Elevation: '+ str(dfp.loc[index,'elevationft']) +' ft"'+ '\n')
        
        fout.write('Text: 15, 10, 1,"' + str(spottername) +'"\n')
        fout.write('End:'+'\n\n') #End
        processnum = processnum + 1 #We added a record!
fout.close()
print('It is Done! Your Placefile contains '+ str(processnum)+ ' positions!')
print('Your placefile is now in the same folder as this .py file called '+ str(pfilename)+'.txt')
