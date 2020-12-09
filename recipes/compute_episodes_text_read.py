import dataiku
import pandas as pd
import numpy as np
import requests
import speech_recognition as sr
import subprocess
from pydub import AudioSegment
import os
import scipy.io.wavfile as wav
from mutagen.mp3 import MP3
import math
import time

episodes_sample = dataiku.Dataset("episodes_sample")
START_ROW = 15
END_ROW = 500
episodes_sample_df = episodes_sample.get_dataframe()
episodes_sample_df = episodes_sample_df.iloc[START_ROW-1:END_ROW-1,:]
#episodes_sample_df = episodes_sample_df.drop(episodes_sample_df.index[[0,2]])

mp3_folder = dataiku.Folder('temp_mp3_folder')
mp3_folder_path = mp3_folder.get_path()
audio_path = mp3_folder_path + '/audio.mp3'
wav_path = mp3_folder_path + '/audio.wav'


ffmpeg_path = '/data/dataiku/data_dir/code-envs/python/ffmpeg_27/bin/ffmpeg/ffmpeg-4.3.1-amd64-static/ffmpeg'

def read_episode(url,length):
    failure_count = 0
    try:
        
        file = requests.get(url)    
        print("pulling mp3 file: " + url)
    except:
        return "failed to pull mp3 file"
    #with mp3_folder.get_writer("audio.mp3") as w:
    #        w.write(file.content)
    try:
        open(audio_path,"wb").write(file.content)
    except:
        return "failed to write file content"
    
    duration = length
    #duration = MP3(audio_path).info.length
    chunk_count = int(math.ceil(duration/30))
    
    s= list()
    
    
    r = sr.Recognizer()
    for c in range(1,chunk_count):
        try:
            subprocess.call([ffmpeg_path,"-y",
                             "-i",audio_path,
                             "-ss",str( max((c-1)*30,1)),
                             "-r","16000",
                             "-ac","1", 
                             "-t","30",
                             wav_path])
        except:
            return "failed to decode mp3 with ffmpeg"
        
        with sr.AudioFile(wav_path) as source:
            try:
                audio = r.record(source)
            except:
                return 'failed_to_read_mp3_file'
            try:
                recognized = r.recognize_google(audio)
            except:
                try:
                    time.sleep(10)
                    r = sr.Recognizer()
                    recognized = r.recognize_google(audio)
                except:
                    try:
                        time.sleep(60)
                        r = sr.Recognizer()
                        recognized = r.recognize_google(audio)
                        failure_count = failure_count+1
                    except:
                        if failure_count % 5 == 0:
                            time.sleep(300)
                        try:
                            r = sr.Recognizer()
                            recognized = r.recognize_google(audio)
                        except:
                            recognized = "google recognized failed"
            s.append( recognized )
        
    
    return s


episodes_read = dataiku.Dataset("episodes_text_read")

episodes_sample_df['text'] = ''
size = 2
for i in range(0, len(episodes_sample_df),size):
    write_df = episodes_sample_df.loc[i:i+size-1,:]
    write_df['text'] = write_df.apply(lambda row: read_episode(row['audio_url'],row['length']), axis=1)
#    writer.write_dataframe(write_df)
    episodes_read.write_with_schema(write_df)
    print("ROWS " + str(i) + ":" + str(i+size-1) + " complete")

    #episodes_sample_df['text'] = episodes_sample_df.apply(lambda row: read_episode(row['audio_url'],row['length']), axis=1)
    
#writer.close()

# Write recipe outputs
#episodes_read = dataiku.Dataset("episodes_text_read")
#episodes_read.write_with_schema(episodes_sample_df)
