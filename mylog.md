copy raw audio to speaker-encode;
```bash
mkdir datasets/LibriSpeech
cp 'audio/AIM 1418.wav' datasets/LibriSpeech
```

created conda env;
```bash
conda create -n rtvc python==3.9 ffmpeg -c conda-forge
conda install pytorch torchvision torchaudio pytorch-cuda=11.7 -c pytorch -c nvidia
pip install -r requirements.txt
```

Preprocess the audio file
```bash
python3 encoder_preprocess.py datasets -d librispeech_other
```

# Encoder
## The project & data structure for training 

clean_data_root
- speaker_dir_1
    - `_sources.txt` contains lines like;
        `frames_fname,wave_filepath` frames_fname is relative to `speaker_dir_<n>`. wave_filepath is not.
    - `frames_fname`: is a .npy file
    - wave_dir
        - `*.wav` the input data
- speaker_dir_2 (becomes speaker name)

### For all in the mind
clean_data_root
 - program_name
    - speaker_dir_1
        - ...
    - speaker_dir_2

old_directory
    audio
        programA_directory
        - <speakerA-name>-1.wav
        - <speakerB-name>-2.wav
        - ...
        - alignments.txt
        programB_directory
        - ...
    transcripts
        programA_directory
        - <speakerA-name>-1.txt
        - <speakerB-name>-2.txt
        - ...
        - metadata.json
        programB_directory
        - ...

`metadata.json`;
```json
{
    "filename": "AIM 1418",
    "group": "2018"
}
```

new_directory
    program_directory
        speakerA_directory
        - _sources.txt    
        - <speakerA-name>-1.wav
        - <speakerA-name>-2.wav
        speakerB_directory
        - _sources.txt
        - <speakerB-name>-3.wav
        - <speakerB-name>-4.wav


# Synthesizer
## The project & data structure for training 
first_dataset_group_name
    speakerA-name
        programA_directory
            - utterance_1.wav
            - utterance_2.wav
            - ...
            - utterance_1.txt ( if no alignments file )
            - utterance_2.txt ( if no alignments file )
            - ...
            - alignments.txt ( if alignments file )
        programB_directory
            - ...
    speakerB-name
        programA_directory
            - ...
second_dataset_group_name


train.txt

`utterance_1.alignment.txt`;
<wav_filename> "<comma separated words>" "<comma separated end_times>"


Given the below metadata in json file below;

```json
[
    {
        "label": "PEOPLE",
        "score": 0.7621903693458686,
        "start_ts": 0.04,
        "end_ts": 0.34,
    },
    {
        "label": "ARE",
        "score": 0.6313090586507334,
        "start_ts": 0.48025,
        "end_ts": 0.60,
    },
]
```
Where `end_ts` is the timestamp of the end of the utterance.

create a text string from the json with the below format;
<wav_filename> "<comma separated words>" "<comma separated end_times>"

Example;
"filename" "PEOPLE,ARE" "0.34,0.60"

Use python to write the function
