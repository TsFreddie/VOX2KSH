import re
import sys

NO_STATE = -1
FORMAT = 0
BEAT = 1
BPM = 2
TILT = 3
LYRIC = 4
END_POSITION = 5
TAB_EFFECT = 6
FXBUTTON = 7
TAB_PARAM = 8
REVERB = 9
TRACK1 = 10
TRACK2 = 11
TRACK3 = 12
TRACK4 = 13
TRACK5 = 14
TRACK6 = 15
TRACK7 = 16
TRACK8 = 17
TRACK_AUTO = 18
SPCONTROLER = 19
SOUND_ID = 20
BPM_SIMPLE = 21

FX_BEAT_VOLUME = 18
TILT_FACTOR = 10
VOL_DRIFT_TOLERANCE = 2

VOL_CHAR = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmno"
FILTER = ["peak", "lpf1", "lpf1", "hpf1", "hpf1", "lbic", "nof"]

ASSUMED_DEFAULT_PITCH = 0.72
CAMERA_DIFFERENCE = 0.0648192846

EFFECT_WEIGHT = {
    4: 100,
    1: 90,
    8: 95,
    2: 85,
    3: 50,
    5: 75,
    6: 80,
    7: 60,
    9: 110,
    10: 30,
    11: 40,
    12: 10,
    0: 0,
}

HEADERS = [
    ("FORMAT VERSION", FORMAT),
    ("BEAT INFO", BEAT),
    ("BPM INFO", BPM),
    ("BPM", BPM_SIMPLE),
    ("TILT MODE INFO", TILT),
    ("LYRIC INFO", LYRIC),
    ("END POSITION", END_POSITION),
    ("TAB EFFECT INFO", TAB_EFFECT),
    ("FXBUTTON EFFECT INFO", FXBUTTON),
    ("TAB PARAM ASSIGN INFO", TAB_PARAM),
    ("REVERB EFFECT PARAM", REVERB),
    ("TRACK1", TRACK1),
    ("TRACK2", TRACK2),
    ("TRACK3", TRACK3),
    ("TRACK4", TRACK4),
    ("TRACK5", TRACK5),
    ("TRACK6", TRACK6),
    ("TRACK7", TRACK7),
    ("TRACK8", TRACK8),
    ("TRACK1 START", TRACK1),
    ("TRACK2 START", TRACK2),
    ("TRACK3 START", TRACK3),
    ("TRACK4 START", TRACK4),
    ("TRACK5 START", TRACK5),
    ("TRACK6 START", TRACK6),
    ("TRACK7 START", TRACK7),
    ("TRACK8 START", TRACK8),
    ("TRACK AUTO TAB", TRACK_AUTO),
    ("SPCONTROLER", SPCONTROLER),
    ("SOUND ID START", SOUND_ID),
]

def str2time(s):
    s_arr = s.split(",")
    if (len(s_arr) != 3):
        return None

    try:
        return (int(s_arr[0]), int(s_arr[1]), int(s_arr[2]))
    except:
        return None

def find_cur_realize(time, realize_list):
    result = realize_list[0][1:]
    for realize in realize_list:
        realize_time = realize[0]
        if realize_time > time:
            break
        else:
            result = realize[1:]
    return result

def realize(overshoot, start, end, t):
    inter = end - start
    extra = overshoot - start
    if (0 <= t <= 1):
        return start + inter * t

    if (t <= 0):
        iteration = 1
        cur_res = 0
        while (t < -1):
            cur_res += -inter * iteration - extra
            t += 1
            iteration += 1

        return start + cur_res + inter*iteration*t + extra*t
    else:
        iteration = 1
        cur_res = 0
        while (t > 1):
            cur_res += inter * iteration + extra
            t -= 1
            iteration += 1

        return start + cur_res + inter*iteration*t + extra*t - extra

def camera_transpose(r):
    deg = (r - ASSUMED_DEFAULT_PITCH - CAMERA_DIFFERENCE) * 57.295779513
    target_deg = (ASSUMED_DEFAULT_PITCH * 57.295779513) + deg
    rot = target_deg // 360
    remain = target_deg % 360
    if (remain >= 0 and remain < 90):
        remain = 959 * remain / 90
    elif (remain >= 90 and remain < 180):
        remain = 959 + 240 * (remain - 90) / 90
    elif (remain >= 180 and remain < 270):
        remain = 1199 + 960 * (remain - 180) / 90
    elif (remain >= 270 and remain < 360):
        remain = 2159 + 241 * (remain - 270) / 90
    return -400 + rot * 2400 + remain

def time2str(t):
    return "%03d,%02d,%02d" % t

def gcd(x, y):
   while(y):
       x, y = y, x % y
   return x

def lcm(x, y):
    return x * y // gcd(x, y)

def current_beat(beats, measure):
    while (measure > 0 and (measure,1,0) not in beats):
        measure -= 1
    if ((measure,1,0) in beats):
        return beats[(measure,1,0)]
    return (4,4)

def advance_time(time, delta, beats):
    measure, beat, sub = time

    beat_sig = current_beat(beats, measure)
    beat_step = (192 // beat_sig[1])
    measure_step = beat_sig[0] * beat_step
    step = (beat-1) * beat_step + sub + delta

    while (step >= measure_step):
        measure += 1
        step -= measure_step
        beat_sig = current_beat(beats, measure)
        beat_step = (192 // beat_sig[1])
        measure_step = beat_sig[0] * beat_step

    while (step < 0):
        measure -= 1
        step += measure_step
        beat_sig = current_beat(beats, measure)
        beat_step = (192 // beat_sig[1])
        measure_step = beat_sig[0] * beat_step

    beat = (step // beat_step)+1
    sub = (step % beat_step)
    note = measure_step // gcd(measure_step, (beat-1) * beat_step + sub)
    return ((measure, beat, sub), abs(note))

def time_difference(time_early, time_late, beats):
    measure, beat, sub = time_early
    measure2, beat2, sub2 = time_late
    steps = 0
    while(measure < measure2):
        beat_sig = current_beat(beats, measure)
        beat_step = (192 // beat_sig[1])
        measure_step = beat_sig[0] * beat_step
        if (beat > 1 or sub > 0):
            cur = (beat-1) * beat_step + sub
            steps += measure_step - cur
            beat = 1
            sub = 0
        else:
            steps += measure_step
        measure += 1

    beat_sig = current_beat(beats, measure2)
    beat_step = (192 // beat_sig[1])
    cur = (beat-1) * beat_step + sub
    cur2 = (beat2-1) * beat_step + sub2
    steps += cur2 - cur
    return steps

def normalize_angle(angle):
    return ((angle + 179) % 360 + 360) % 360 - 179


def interp_vol_values(measures, tracks, vol, vol_interp, beats, end_slam):
    interp_points = vol_interp[vol]
    len_points = len(interp_points)
    track_id = vol * 7

    if (len_points < 2):
        return

    if (len_points == 2):
        if (interp_points[0][2]):
            # high res come from slam, try to compress the prev slam to give more room for line.
            data = interp_points[0][1]
            data = (data[0], data[1], data[2], data[3], data[4], data[5], True)
            tracks[track_id][interp_points[0][0]] = data

            back_time, back_note = advance_time(interp_points[0][0], -2, beats)
            back_measure = back_time[0]
    
            if (back_measure not in measures):
                measures[back_measure] = back_note
            else:
                measures[back_measure] = lcm(measures[back_measure], back_note)

            tracks[track_id][back_time] = interp_points[0][1]
        elif (interp_points[0][1][1] == 0):
            data = interp_points[0][1]
            data = (data[0], data[1], data[2], data[3], data[4], data[5], True)
            tracks[track_id][interp_points[0][0]] = data
            print("Warning: dropping enclosed sample at:", interp_points[0][0])
        elif (interp_points[1][1][1] == 0):
            data = interp_points[1][1]
            data = (data[0], data[1], data[2], data[3], data[4], data[5], True)
            tracks[track_id][interp_points[1][0]] = data
            print("Warning: dropping enclosed sample at:", interp_points[1][0])
        else:
            print("Warning: impossible interp at:", interp_points[0][0], interp_points[1][0])
        interp_points.clear()
        return

        
    # print("hi-res secion ends at:", interp_points)
    
    if (len_points % 2 == 1):
        # odd sections: halfing the samples
        for i in range(len_points):
            data = interp_points[i][1]
            if (i != len_points - 1 and i % 2 == 1):
                data = (data[0], data[1], data[2], data[3], data[4], data[5], True)
            tracks[track_id][interp_points[i][0]] = data
            # print(track_id, interp_points[i][0], data)
    else:
        sections = len_points - 1
        pulses = sections * 6
        step = -1
        for j in range(9, pulses):
            if pulses % j == 0:
                step = j
                break
        
        cur = 0
        cur_time = interp_points[0][0]

        # ghostify all points in between
        for i in range(1, len_points - 1):
            data = interp_points[i][1]
            data = (data[0], data[1], data[2], data[3], data[4], data[5], True)
            tracks[track_id][interp_points[i][0]] = data

        while (cur < pulses):
            cur += step
            if (cur >= pulses):
                break
            
            cur_time, cur_note = advance_time(cur_time, step, beats)
            if (cur_time in tracks[track_id]):
                # un-ghostify matching points
                data = tracks[track_id][cur_time]
                data = (data[0], data[1], data[2], data[3], data[4], data[5], False)
                tracks[track_id][cur_time] = data
                continue

            start_idx = cur // 6
            start_pulse = start_idx * 6
            end_pulse = (start_idx + 1) * 6
            start_point = interp_points[start_idx][1]
            end_point = interp_points[start_idx + 1][1]

            value = start_point[0] + ((cur - start_pulse) / (end_pulse - start_pulse)) * (end_point[0] - start_point[0])


            data = (int(value), start_point[1], start_point[2], start_point[3], start_point[4], start_point[5], False)
            tracks[track_id][cur_time] = data
            # print("inter:", track_id, cur_time, data)
            cur_measure = cur_time[0]
            if (cur_measure not in measures):
                measures[cur_measure] = cur_note
            else:
                measures[cur_measure] = lcm(measures[cur_measure], cur_note)

    interp_points.clear()
    return

def readvox(filename):
    # Read object
    version = -1
    beats = {}
    bpms = {}
    tracks = [{} for i in range(8)]
    measures = {}
    effects = []
    effects2 = []
    effect_is_filter = set()
    zoom_top = {}
    zoom_bottom = {}
    tilt = {}
    lane_toggle = {}
    stop = {}
    end = None
    custom_filter = {}
    zoom_top_realize = []
    zoom_bottom_realize = []
    tab_param = {}

    prev_zoom_top = None
    prev_zoom_bottom = None

    prev_stop = None

    last_measure = None

    prev_tilt = None

    prev_vol = [None, None]
    vol_interp = [[], []]

    state = -1
    line_num = 0

    tab_cleaner = re.compile(r"\t+")

    with open(filename, 'r', encoding="cp932") as f:
        while True:
            line = f.readline()
            if (not line):
                break

            line = line.strip()
            line = tab_cleaner.sub("\t", line)

            line_num += 1

            if (len(line) == 0):
                continue

            if (line == "#END"):
                state = NO_STATE
                continue

            if (line.startswith("//")):
                continue

            if (state != NO_STATE and line.startswith("#")):
                continue

            #region [rgba(0, 32, 0, 0.5)] NO_STATE
            if (state == NO_STATE):
                if (line.startswith("#")):
                    mode = line[1:]
                    for header in HEADERS:
                        if (mode == header[0]):
                            state = header[1]
                            break
            #endregion
            # #region [rgba(64, 32, 0, 0.5)] SOUND_ID
            # elif (state == SOUND_ID):
            #     data = line.split('\t')
            #     try:
            #         fx_audio[data[1]] = int(data[2])
            #     except:
            #         print("[SOUND_ID Error] cannot parse line at %d" % line_num)
            # #endregion
            #region [rgba(32, 32, 0, 0.5)] FORMAT
            elif (state == FORMAT):
                try:
                    version = int(line)
                except:
                    print("[FORMAT Error] cannot parse line at %d" % line_num)
            #endregion
            #region [rgba(64, 32, 64, 0.5)] FXS
            elif (state == FXBUTTON):
                data = line.split(',\t')
                target = effects

                if (version >= 6 and len(effects2) < len(effects)):
                    target = effects2

                try:
                    target.append([float(param) if "." in param else int(param) for param in data])
                except:
                    print("[FXBUTTON Error] cannot parse line at %d" % line_num)
            #endregion
            #region [rgba(0, 32, 32, 0.5)] BEAT
            elif (state == BEAT):
                data = line.split('\t')
                if (len(data) != 3):
                    print("[BEAT Error] wrong format at %d" % line_num)
                    continue

                time = str2time(data[0])
                if (time is None):
                    print("[BEAT Error] wrong time format at %d" % line_num)
                    continue
                measure, beat, sub = time
                if (beat != 1 or sub != 0):
                    print("[BEAT Error] a beat change appeared not at the start of a measure: %d" % line_num)
                    continue
                try:
                    beats[time] = (int(data[1]), int(data[2]))
                except:
                    print("[BEAT Error] cannot parse line at %d" % line_num)

                if (measure not in measures):
                    measures[measure] = 1

                if (last_measure is None or measure > last_measure):
                    last_measure = measure

            #endregion
            #region [rgba(0, 32, 0, 0.5)] BPM_SIMPLE
            elif (state == BPM_SIMPLE):
                try:
                    bpm = float(line)
                    bpms[(1,1,0)] = (bpm, 4)
                except:
                    print("[BPM_SIMPLE Error] cannot parse line at %d" % line_num)
            #endregion
            #region [rgba(0, 32, 64 ,0.5)] BPM
            elif (state == BPM):
                data = line.split('\t')

                if (len(data) < 3):
                    print("[BPM Error] wrong format at %d" % line_num)
                    continue

                if (data[1].startswith("BAR")):
                    # skip special instructions
                    continue

                time = str2time(data[0])
                if (time is None):
                    print("[BPM Error] wrong time format at %d" % line_num)
                    continue

                measure, beat, sub = time
                beat_sig = current_beat(beats, measure)
                beat_step = (192 // beat_sig[1])
                measure_step = beat_sig[0] * beat_step
                note = measure_step // gcd(measure_step, (beat-1) * beat_step + sub)

                try:
                    if data[2].endswith("-"):
                        if (prev_stop is None):
                            prev_stop = time
                        data[2] = data[2][:-1]
                    else:
                        if (prev_stop is not None):
                            stop[prev_stop] = time_difference(prev_stop, time, beats)
                            prev_stop = None
                    bpms[time] = (float(data[1]), int(data[2]))
                except:
                    print("[BPM Error] cannot parse line at %d" % line_num)
                    continue

                if (bpms[time][1] != 4):
                    print("[BPM Warning] unknown bpm param at line %d" % line_num)

                if (measure not in measures):
                    measures[measure] = note
                else:
                    measures[measure] = lcm(measures[measure], note)

                if (last_measure is None or measure > last_measure):
                    last_measure = measure
            #endregion
            #region [rgba(32, 16, 256, 0.5)] TAB_PARAM
            elif (state == TAB_PARAM):
                data = line.split(',\t')

                fx_id = int(data[0])
                param_id = int(data[1])

                if (param_id > 0):
                    if (fx_id not in tab_param):
                        tab_param[fx_id] = {}
                    if (param_id not in tab_param[fx_id]):
                        tab_param[fx_id][param_id] = (float(data[2]), float(data[3]))
                    else:
                        tab_param[fx_id][param_id] = (
                            (tab_param[fx_id][param_id][0] + float(data[2])) / 2,
                            (tab_param[fx_id][param_id][1] + float(data[3])) / 2
                        )
            #endregion
            #region [rgba(32, 16, 128, 0.5)] TRACK_AUTO
            elif (state == TRACK_AUTO):
                data = line.split('\t')

                alt_note = -1
                alt_measure = -1

                time = str2time(data[0])
                if (time is None):
                    print("[TRACK_AUTO Error] wrong time format at %d" % line_num)
                    continue

                measure, beat, sub = time
                beat_sig = current_beat(beats, measure)
                beat_step = (192 // beat_sig[1])
                measure_step = beat_sig[0] * beat_step
                note = measure_step // gcd(measure_step, cur)

                try:
                    filter_duration = int(data[1])
                    effect_type = int(data[2])
                    custom_filter[time] = (effect_type, filter_duration)
                    alt_time, alt_note = advance_time(time, filter_duration, beats)
                    alt_measure = alt_time[0]
                    effect_is_filter.add(effect_type)
                except:
                    print("[TRACK_AUTO Error] cannot parse line at %d" % line_num)
                    continue

                if (measure not in measures):
                    measures[measure] = note
                else:
                    measures[measure] = lcm(measures[measure], note)

                if (alt_note > 0 and alt_measure > 0):
                    if (alt_measure not in measures):
                        measures[alt_measure] = alt_note
                    else:
                        measures[alt_measure] = lcm(measures[alt_measure], alt_note)

            #endregion
            #region [rgba(2, 64, 128 ,0.5)] TRACKS
            elif (state >= TRACK1 and state <= TRACK8):
                track_id = state - TRACK1
                data = line.split('\t')

                time = str2time(data[0])
                if (time is None):
                    print("[TRACK Error] wrong time format at %d" % line_num)
                    continue

                measure, beat, sub = time
                beat_sig = current_beat(beats, measure)
                beat_step = (192 // beat_sig[1])
                measure_step = beat_sig[0] * beat_step

                cur = (beat-1) * beat_step + sub
                note = measure_step // gcd(measure_step, cur)

                alt_note = -1
                alt_measure = -1
                mid_note = -1
                mid_measure = -1

            #endregion #region [rgba(128, 64, 128 ,0.5)] Knobs
                if (track_id == 0 or track_id == 7):
                    #knob
                    if (len(data) < 4):
                        print("[TRACK Error] wrong format at %d" % line_num)
                        continue
                    try:
                        wide = False
                        extra = 0
                        sound_type = 0
                        if (len(data) >= 5):
                            sound_type = int(data[4])
                        if (len(data) >= 6):
                            wide = int(data[5]) == 2
                        if (len(data) >= 7):
                            extra = int(data[6])

                        vol = track_id // 7

                        if (time in tracks[track_id]):
                            if (len(vol_interp[vol]) > 0):
                                interp_vol_values(measures, tracks, vol, vol_interp, beats, True)
                            # Slam
                            mid_time, mid_note = advance_time(time, 4, beats)
                            alt_time, alt_note = advance_time(time, 6, beats)
                            tracks[track_id][alt_time] = (int(data[1]), int(data[2]), int(data[3]), sound_type, wide, extra, False) # False -> not ghost
                            alt_measure = alt_time[0]
                            mid_measure = mid_time[0]

                            prev_vol[vol] = (alt_time, tracks[track_id][alt_time], True)
                        else:
                            tracks[track_id][time] = (int(data[1]), int(data[2]), int(data[3]), sound_type, wide, extra, False)
                            # give end note a bit head room (see XROSS THE XOUL)
                            if (tracks[track_id][time][1] == 2):
                                alt_time, alt_note = advance_time(time, 12, beats)
                                alt_measure = alt_time[0]

                            vol_buf_data = (time, tracks[track_id][time], False)

                            if (prev_vol[vol] is not None):
                                time_diff = time_difference(prev_vol[vol][0], time, beats)
                                if (time_diff == 6):
                                    if (len(vol_interp[vol]) == 0):
                                        vol_interp[vol].append(prev_vol[vol])
                                    vol_interp[vol].append(vol_buf_data)
                                elif (time_diff < 6):
                                    if (not prev_vol[vol][2]):
                                        print("Warning: unhandled laser at:", time, time_diff)
                                    if (len(vol_interp[vol]) > 0):
                                        interp_vol_values(measures, tracks, vol, vol_interp, beats, False)
                                else:
                                    if (len(vol_interp[vol]) > 0):
                                        interp_vol_values(measures, tracks, vol, vol_interp, beats, False)

                            prev_vol[vol] = vol_buf_data
                    except:
                        print("[TRACK Error] cannot parse line at %d" % line_num)
                        continue
            #endregion #region [rgba(128, 90, 38,0.5)] FX
                elif (track_id == 1 or track_id == 6):
                    #fx
                    if (len(data) < 3):
                        print("[TRACK Error] wrong format at %d" % line_num)
                        continue
                    try:
                        # if (len(data) >= 4):
                        #     fx_audio_name = data[3]
                        #     fx_audio_id = 0
                        #     if (fx_audio_name in fx_audio):
                        #         fx_audio_id = fx_audio[fx_audio_name]
                        #     tracks[track_id][time] = (int(data[1]), int(data[2]), fx_audio_id)
                        # else:
                        tracks[track_id][time] = (int(data[1]), int(data[2]), 0)
                    except:
                        print("[TRACK Error] cannot parse line at %d" % line_num)
                        continue

                    if (tracks[track_id][time][0] > 0):
                        alt_note = measure_step
                        if tracks[track_id][time][0] % 2 == 0:
                            mid_time, mid_note = advance_time(time, tracks[track_id][time][0] // 2, beats)
                        alt_time, alt_note = advance_time(time, tracks[track_id][time][0], beats)
                        alt_measure = alt_time[0]
                        mid_measure = mid_time[0]
            #endregion #region [rgba(128, 128, 128, 0.5)] BT
                else:
                    #bt
                    if (len(data) < 3):
                        print("[TRACK Error] wrong format at %d" % line_num)
                        continue
                    try:
                        tracks[track_id][time] = (int(data[1]), int(data[2]))
                    except:
                        print("[TRACK Error] cannot parse line at %d" % line_num)
                        continue
                    if (tracks[track_id][time][0] > 0):
                        alt_note = 192

                        if tracks[track_id][time][0] % 2 == 0:
                            mid_time, mid_note = advance_time(time, tracks[track_id][time][0] // 2, beats)
                        alt_time, alt_note = advance_time(time, tracks[track_id][time][0], beats)
                        alt_measure = alt_time[0]
                        mid_measure = mid_time[0]

                if (measure not in measures):
                    measures[measure] = note
                else:
                    measures[measure] = lcm(measures[measure], note)

                if (alt_note > 0 and alt_measure > 0):
                    if (alt_measure not in measures):
                        measures[alt_measure] = alt_note
                    else:
                        measures[alt_measure] = lcm(measures[alt_measure], alt_note)

                if (mid_note > 0 and mid_measure > 0):
                    if (mid_measure not in measures):
                        measures[mid_measure] = mid_note
                    else:
                        measures[mid_measure] = lcm(measures[mid_measure], mid_note)

                if (last_measure is None or measure > last_measure):
                    last_measure = measure

                if (last_measure is None or alt_measure > last_measure):
                    last_measure = alt_measure

            #endregion #region [rgba(0, 128, 128, 0.5)] TILT
            elif (state == TILT):
                data = line.split('\t')
                if (len(data) < 2):
                    print("[TILT Error] wrong format at %d" % line_num)
                    continue
                time = str2time(data[0])
                if (time is None):
                    print("[TILT Error] wrong time format at %d" % line_num)
                    continue

                measure, beat, sub = time
                beat_sig = current_beat(beats, measure)
                beat_step = (192 // beat_sig[1])
                measure_step = beat_sig[0] * beat_step

                cur = (beat-1) * beat_step + sub
                note = measure_step // gcd(measure_step, cur)

                try:
                    tilt_mode = int(data[1])
                    if tilt_mode == 0:
                        prev_tilt = "normal"
                    elif tilt_mode == 1:
                        prev_tilt = "bigger"
                    elif tilt_mode == 2:
                        prev_tilt = "keep_bigger"
                    else:
                        print("[TILT Error] Unknown tilt mode %d" % tilt_mode)
                        prev_tilt = None
                except:
                    print("[TILT Error] cannot parse tilt mode at %d" % line_num)
                    prev_tilt = None
                    continue

                if (prev_tilt is not None):
                    if (time in tilt):
                        tilt[time].append(prev_tilt)
                    else:
                        tilt[time] = [prev_tilt]

                if (measure not in measures):
                    measures[measure] = note
                else:
                    measures[measure] = lcm(measures[measure], note)

                if (last_measure is None or measure > last_measure):
                    last_measure = measure
            #endregion #region [rgba(72, 64, 256, 0.5)] SPCONTROLLER
            elif (state == SPCONTROLER):
                data = line.split('\t')
                if (len(data) < 2):
                    print("[SP Error] wrong format at %d" % line_num)
                    continue
                time = str2time(data[0])
                if (time is None):
                    print("[SP Error] wrong time format at %d" % line_num)
                    continue

                measure, beat, sub = time
                beat_sig = current_beat(beats, measure)
                beat_step = (192 // beat_sig[1])
                measure_step = beat_sig[0] * beat_step

                cur = (beat-1) * beat_step + sub
                note = measure_step // gcd(measure_step, cur)

                alt_note = -1
                alt_measure = -1

                camera_op = data[1]

                if (camera_op == "CAM_RotX"):
                    # zoom_top
                    try:
                        duration = int(float(data[3]))
                        rover, rstart, rend = find_cur_realize(time, zoom_top_realize)
                        from_pos = realize(rover, rstart, rend, float(data[4]))

                        to_pos = realize(rover, rstart, rend, float(data[5]))
                        alt_time, alt_note = advance_time(time, duration, beats)
                        alt_measure = alt_time[0]

                        if (time in zoom_top):
                            if (prev_zoom_top is not None):
                                zoom_top[time].append(prev_zoom_top)
                            zoom_top[time].append(from_pos)
                        else:
                            if (prev_zoom_top is not None):
                                zoom_top[time] = [prev_zoom_top, from_pos]
                            else:
                                zoom_top[time] = [from_pos]

                        if (alt_time in zoom_top):
                            zoom_top[alt_time].append(to_pos)
                        else:
                            zoom_top[alt_time] = [to_pos]

                        prev_zoom_top = to_pos
                    except:
                        print("[SP Error] cannot parse CAM_RotX at %d" % line_num)
                        continue

                elif (camera_op == "CAM_Radi"):
                    # zoom_bottom
                    try:
                        duration = int(float(data[3]))
                        rover, rstart, rend = find_cur_realize(time, zoom_bottom_realize)
                        from_pos = realize(rover, rstart, rend, float(data[4]))
                        to_pos = realize(rover, rstart, rend, float(data[5]))
                        alt_time, alt_note = advance_time(time, duration, beats)
                        alt_measure = alt_time[0]

                        if (time in zoom_bottom):
                            if (prev_zoom_bottom is not None):
                                zoom_bottom[time].append(prev_zoom_bottom)
                            zoom_bottom[time].append(from_pos)
                        else:
                            if (prev_zoom_bottom is not None):
                                zoom_bottom[time] = [prev_zoom_bottom, from_pos]
                            else:
                                zoom_bottom[time] = [from_pos]

                        if (alt_time in zoom_bottom):
                            zoom_bottom[alt_time].append(to_pos)
                        else:
                            zoom_bottom[alt_time] = [to_pos]

                        prev_zoom_bottom = to_pos
                    except:
                        print("[SP Error] cannot parse CAM_Radi at %d" % line_num)
                        continue
                elif (camera_op == "BIL_RotZ"):
                    # tilt
                    try:
                        duration = int(float(data[3]))
                        from_pos = float(data[4][1:])
                        new_from_pos = normalize_angle(from_pos)
                        from_delta = new_from_pos - from_pos
                        to_pos = float(data[5][1:])
                        to_pos += from_delta
                        new_to_pos = normalize_angle(to_pos)

                        alt_time, alt_note = advance_time(time, duration, beats)
                        alt_measure = alt_time[0]

                        new_from_pos = new_from_pos / TILT_FACTOR
                        to_pos = to_pos / TILT_FACTOR
                        new_to_pos = new_to_pos / TILT_FACTOR

                        if (time in tilt):
                            tilt[time].append(new_from_pos)
                        else:
                            tilt[time] = [new_from_pos]

                        if (alt_time in tilt):
                            tilt[alt_time].append(to_pos)
                        else:
                            tilt[alt_time] = [to_pos]

                        if (new_to_pos != to_pos):
                            tilt[alt_time].append(new_to_pos)

                        if (new_to_pos == 0):
                            tilt[alt_time].append("normal")

                    except:
                        print("[SP Error] cannot parse BIL_RotZ at %d" % line_num)
                        continue
                elif (camera_op == "Tilt"):
                    # tilt
                    try:
                        duration = int(float(data[3]))
                        from_pos = -float(data[4]) * 1.5
                        to_pos = -float(data[5]) * 1.5

                        alt_time, alt_note = advance_time(time, duration, beats)
                        alt_measure = alt_time[0]

                        if (time in tilt):
                            tilt[time].append(from_pos)
                        else:
                            tilt[time] = [from_pos]

                        if (alt_time in tilt):
                            tilt[alt_time].append(to_pos)
                        else:
                            tilt[alt_time] = [to_pos]

                        if (to_pos == 0):
                            tilt[alt_time].append("normal")

                    except:
                        print("[SP Error] cannot parse Tilt at %d" % line_num)
                        continue
                elif (camera_op == "LaneY"):
                    # lane_toggle
                    # TODO: maybe wait for a new format in usc
                    try:
                        duration = int(float(data[3]))
                        hide_lane = float(data[4]) < float(data[5])

                        if (time in tilt):
                            lane_toggle[time].append((duration, hide_lane))
                        else:
                            lane_toggle[time] = [(duration, hide_lane)]
                    except:
                        print("[SP Error] cannot parse LaneY at %d" % line_num)
                        continue
                elif (camera_op == "Realize"):
                    try:
                        if int(data[2]) == 3:
                            zoom_bottom_realize.append((time, float(data[4]), float(data[5]), float(data[6])))
                        elif int(data[2]) == 4:
                            zoom_top_realize.append((time, float(data[4]), float(data[5]), float(data[6])))
                    except:
                        print("[SP Error] cannot parse Realize at %d" % line_num)
                        continue
                if (measure not in measures):
                    measures[measure] = note
                else:
                    measures[measure] = lcm(measures[measure], note)

                if (alt_note > 0 and alt_measure > 0):
                    if (alt_measure not in measures):
                        measures[alt_measure] = alt_note
                    else:
                        measures[alt_measure] = lcm(measures[alt_measure], alt_note)

                if (last_measure is None or measure > last_measure):
                    last_measure = measure

                if (last_measure is None or alt_measure > last_measure):
                    last_measure = alt_measure

            #endregion
            elif (state == END_POSITION):
                time = str2time(line)
                if (time is None):
                    print("[END POS Error] wrong time format at %d" % line_num)
                    continue
                end = time

    # clear interp
    interp_vol_values(measures, tracks, 0, vol_interp, beats, False)
    interp_vol_values(measures, tracks, 1, vol_interp, beats, False)

    if (prev_stop is not None):
        stop[prev_stop] = time_difference(prev_stop, end, beats)

    if (end is None):
        end = (last_measure+1, 0, 0)

    return (version, (effects, effects2, effect_is_filter), (zoom_top, zoom_bottom, tilt, lane_toggle), beats, bpms, tracks, custom_filter, tab_param, measures, stop, end)

def map2kshbeats(bmap, fx = None):
    version, effects, camera, beats, bpms, tracks, custom_filter, tab_param, measures, stop, end = bmap

    fx_names = [{}, {}]
    fx_mix = {}

    fx_beats = set()

    # Effects
    emap = ""
    if fx is not None:
        emap += "#define_fx FX_TRACK type=SwitchAudio;fileName=%s\n" % (fx)

    allowed_filters = {}
    for i in range(len(effects[0])):
        name = "FX%d" % i
        left_name = None
        right_name = None
        effect = effects[0][i]

        # Choose one effect using weight
        if i < len(effects[1]) and effects[1][i][0] in EFFECT_WEIGHT:
            fx2_weight = EFFECT_WEIGHT[effects[1][i][0]]
            fx_weight = EFFECT_WEIGHT[effect[0]]
            if fx2_weight > fx_weight:
                effect = effects[1][i]

        fx_type = effect[0]
        mix = None
        if (fx_type == 1 or fx_type == 8):
            filter_force_trigger = False
            # Retrigger
            if (float(effect[4]) == 1 and float(effect[3]) >= 0):
                mix = int(effect[2])
                period = (effect[3] / 4)
                wavelength = (float(effect[1] / effect[3]) * 4)
                if (wavelength <= 0):
                    wavelength = 1

                if (wavelength >= 128):
                    mix = int(mix * 0.6)
                if (wavelength >= 64):
                    mix = int(mix * 0.8)
                if (fx_type == 8):
                    left_name = "%s_L;%f\nfx:%s_L:updateTrigger=on" % (name, wavelength, name)
                    right_name = "%s_R;%f\nfx:%s_R:updateTrigger=on" % (name, wavelength, name)
                else:
                    left_name = "%s_L;%f" % (name, wavelength)
                    right_name = "%s_R;%f" % (name, wavelength)
                emap += "#define_fx %s_L type=Retrigger;rate=%d%%;mix=%d%%>%d%%;updatePeriod=%f\n" % (name, effect[5] * 80, 0, mix, period)
                emap += "#define_fx %s_R type=Retrigger;rate=%d%%;mix=%d%%>%d%%;updatePeriod=%f\n" % (name, effect[5] * 80, 0, mix, period)

                #Retrigger Tab
                wavelength_tab = str(1/wavelength)
                period_tab = str(effect[3] / 4)
                mix_tab = str(mix)
                rate_tab = str(effect[5] * 80)

                if (i in tab_param):
                    params = tab_param[i]
                    if (5 in params):
                        rate_tab = str(int(params[5][0] * 80)) +"%" + "-" + str(int(params[5][1] * 80))+"%"

                    if (1 in params or 3 in params):
                        filter_force_trigger = True
                    
                    mix_low = int(params[2][0]) if 2 in params else int(effect[2])
                    mix_high = int(params[2][1]) if 2 in params else int(effect[2])
                    param3_low = float(params[3][0]) if 3 in params else effect[3]
                    param3_high = float(params[3][1]) if 3 in params else effect[3]
                    param1_low = float(params[1][0]) if 1 in params else effect[1]
                    param1_high = float(params[1][1]) if 1 in params else effect[1]

                    period_low = (param3_low / 4)
                    period_high = (param3_high / 4)

                    wl_low = (float(param1_low / param3_low) * 4)
                    if (wl_low <= 0):
                        wl_low = 1
                    if (wl_low >= 128):
                        mix_low = int(mix_low * 0.6)
                    if (wl_low >= 64):
                        mix_low = int(mix_low * 0.8)

                    wl_high = (float(param1_high / param3_high) * 4)
                    if (wl_high <= 0):
                        wl_high = 1
                    if (wl_high >= 128):
                        mix_high = int(mix_high * 0.6)
                    if (wl_high >= 64):
                        mix_high = int(mix_high * 0.8)

                    mix_tab = str(mix_low)+"%" + "-" + str(mix_high)+"%"
                    period_tab = str(period_low) + "-" + str(period_high)
                    wavelength_tab = str(1/wl_low) + "-" + str(1/wl_high)
                
                if (i+2 in effects[2]):
                    emap += "#define_filter ft%d type=Retrigger;waveLength=%s;rate=%s;mix=%d%%>%s;updatePeriod=%s\n" % (i, wavelength_tab, rate_tab, 0, mix_tab, period_tab)
            else:
                # Echo
                mix = int(effect[2])
                # new_type = (";updatePeriod=%f" % (abs(float(effect[3]))))
                new_type = (";updatePeriod=0") # default to no update?
                feedback = effect[4] * 115
                if feedback > 95:
                    feedback = 95

                if (effect[3] < 0):
                    feedback = 90
                    mix = int(effect[2]) * 0.85

                effect[3] = abs(float(effect[3]))
                wavelength = (float(effect[1] / effect[3]) * 4)
                if (wavelength <= 0):
                    wavelength = 1

                if (fx_type == 8):
                    left_name = "%s_L;%d;%d%%\nfx:%s_L:updateTrigger=on" % (name, wavelength, feedback, name)
                    right_name = "%s_R;%d;%d%%\nfx:%s_R:updateTrigger=on" % (name, wavelength, feedback, name)
                else:
                    left_name = "%s_L;%d;%d%%" % (name, wavelength, feedback)
                    right_name = "%s_R;%d;%d%%" % (name, wavelength, feedback)
                emap += "#define_fx %s_L type=Echo;mix=%d%%>%d%%%s\n" % (name, 0, mix, new_type)
                emap += "#define_fx %s_R type=Echo;mix=%d%%>%d%%%s\n" % (name, 0, mix, new_type)
                if (i+2 in effects[2]):
                    emap += "#define_filter ft%d type=Echo;waveLength=%f;feedbackLevel=%d%%;mix=%d%%>%d%%%s\n" % (i, 1/wavelength, feedback, 0, mix, new_type)
            allowed_filters[i] = fx_type == 8 or filter_force_trigger
        elif (fx_type == 2):
            # Gate
            mix = float(effect[1]) * 0.75
            rate = float(effect[3])
            emap += "#define_fx %s type=Gate;rate=%d%%;mix=%d%%>%d%%\n" % (name, rate * 60, 0, mix)
            wavelength = (effect[2] * 2)
            if (wavelength <= 0):
                wavelength = 1
            name += ";%d" % (wavelength)

            rate_tab = str(float(effect[3]) * 60) + "%"
            if (i in tab_param):
                if (3 in tab_param[i]):
                    rate_tab = str(float(tab_param[i][3][0]) * 60) + "%" + "-" + str(float(tab_param[i][3][1]) * 60) + "%"

            wavelength_tab = str(1 / wavelength)
            if (i in tab_param):
                if (2 in tab_param[i]):
                    wl_low = float(tab_param[i][2][0]) * 2
                    if (wl_low <= 0):
                        wl_low = 1
                    wl_high = float(tab_param[i][2][1]) * 2
                    if (wl_high <= 0):
                        wl_high = 1
                    wavelength_tab = str(1 / wl_low) + "-" + str(1 / wl_high)

            if (i+2 in effects[2]):
                emap += "#define_filter ft%d type=Gate;waveLength=%s;rate=%s;mix=%d%%>%d%%\n" % (i, wavelength_tab, rate_tab, 0, mix)
            allowed_filters[i] = False
        elif (fx_type == 3):
            # Flanger
            mix = float(effect[1])
            emap += "#define_fx %s type=Flanger;stereoWidth=100%%;period=%f;delay=%dsamples;depth=%dsamples;mix=%d%%>%d%%;volume=100%%\n" % (name, effect[3], effect[4], effect[4], 0, mix)
            # if (i+2 in effects[2]):
            #     emap += "#define_filter ft%d type=Flanger;period=%f;delay=%dsamples;depth=%dsamples;mix=%d%%>%d%%;volume=95%%\n" % (i, effect[3], effect[4], effect[4], 0, mix)
        elif (fx_type == 4):
            # Stop
            mix = float(effect[1])
            emap += "#define_fx %s_L type=TapeStop;mix=%d%%>%d%%\n" % (name, 0, mix)
            emap += "#define_fx %s_R type=TapeStop;mix=%d%%>%d%%\n" % (name, 0, mix)

            # Sound Accurate
            speed = (50 - effect[3] * 50)

            # Time Accurate
            # speed = 17.3 - 0.583 * float(effect[3]) / (float(effect[3]) + 0.1)

            if (speed > 100):
                speed = 100
            if (speed < 1):
                speed = 1
            left_name = "%s_L;%d" % (name, speed)
            right_name = "%s_R;%d" % (name, speed)

            speed_tab = str(int(17.3 - 0.583 * float(effect[3]) / (float(effect[3]) + 0.1))) + "%"
            if (i in tab_param):
                if (3 in tab_param[i]):
                    speed_low = 17.3 - 0.583 * float(tab_param[i][3][0]) / (float(tab_param[i][3][0]) + 0.1)
                    if (speed_low > 100):
                        speed_low = 100
                    if (speed_low < 1):
                        speed_low = 1
                    speed_high = 17.3 - 0.583 * float(tab_param[i][3][1]) / (float(tab_param[i][3][1]) + 0.1)
                    if (speed_high > 100):
                        speed_high = 100
                    if (speed_high < 1):
                        speed_high = 1
                    speed_tab = str(int(speed_low)) + "%" + "-" + str(int(speed_high)) + "%"

            if (i+2 in effects[2]):
                emap += "#define_filter ft%d type=TapeStop;mix=%d%%>%d%%;speed=%s\n" % (i, 0, mix, speed_tab)
            allowed_filters[i] = False
        elif (fx_type == 5):
            # Sidechain
            emap += "#define_fx %s type=SideChain;period=%f\n" % (name, 1 / (float(effect[2]) * 2))

            period_tab = 1 / (float(effect[2]) * 2)
            if (i in tab_param):
                if (2 in tab_param[i]):
                    period_tab = str(1 / (float(tab_param[i][2][0]) * 2)) + "-" + str(1 / (float(tab_param[i][2][1]) * 2))

            if (i+2 in effects[2]):
                emap += "#define_filter ft%d type=SideChain;period=%s\n" % (i, period_tab)
            allowed_filters[i] = False
        elif (fx_type == 6):
            # Wobble
            mix = float(effect[3])
            emap += "#define_fx %s type=Wobble;loFreq=%dHz;hiFreq=%dHz;Q=%f;mix=%d%%>%d%%\n" % (name, effect[4], effect[5], effect[7], 0, mix)
            wavelength = 4 * float(effect[6])
            if wavelength <= 0:
                wavelength = 1
            name += ";%d" % wavelength
            # if (i+2 in effects[2]):
            #     emap += "#define_filter ft%d type=Wobble;loFreq=%dHz;hiFreq=%dHz;Q=%f;mix=%d%%>%d%%;waveLength=%f\n" % (i, effect[4], effect[5], effect[7], 0, mix, 1/wavelength)
        elif (fx_type == 7):
            # BitCrusher
            mix = float(effect[1])
            emap += "#define_fx %s type=BitCrusher;mix=%d%%>%d%%\n" % (name, 0, mix)
            name += ";%d" % (abs(float(effect[2])))

            # tab param
            reduction_tab = str(abs(effect[2]))
            if (i in tab_param):
                if (2 in tab_param[i]):
                    reduction_tab = str(abs(float(tab_param[i][2][0]))) + "-" + str(abs(float(tab_param[i][2][1])))

            if (i+2 in effects[2]):
                emap += "#define_filter ft%d type=BitCrusher;mix=%d%%>%d%%;reduction=%ssamples\n" % (i, 0, mix, reduction_tab)
            allowed_filters[i] = False
        elif (fx_type == 9):
            # PitchShift
            mix = float(effect[1])
            emap += "#define_fx %s type=PitchShift;mix=%d%%>%d%%\n" % (name, 0, mix)
            name += ";%d" % (effect[2])

            # tab param
            pitch_tab = str(effect[2])
            if (i in tab_param):
                if (2 in tab_param[i]):
                    pitch_tab = str(tab_param[i][2][0]) + "-" + str(tab_param[i][2][1])

            if (i+2 in effects[2]):
                emap += "#define_filter ft%d type=PitchShift;mix=%d%%>%d%%;pitch=%s\n" % (i, 0, mix, pitch_tab)
            allowed_filters[i] = False
        elif (fx_type == 10):
            # Don't know pretty subtle, just treat it as phaser for good measure
            mix = float(effect[1])
            emap += "#define_fx %s type=Phaser;mix=%d%%>%d%%;Q=%f\n" % (name, 0, mix, effect[2])
            # if (i+2 in effects[2]):
            #     emap += "#define_filter ft%d type=Phaser;mix=%d%%>%d%%;Q=%f\n" % (i, 0, mix, effect[2])
        elif (fx_type == 11):
            # Low pass - use wobble
            mix = float(effect[1])

            emap += "#define_fx %s type=Wobble;mix=%d%%>%d%%;loFreq=%dHz;hiFreq=%dHz;Q=4.5\n" % (name, 0, mix, effect[3], effect[3])
            name += ";8"

            # tab param
            freq = str(int(effect[3]))
            if (i in tab_param):
                if (3 in tab_param[i]):
                    freq = str(int(tab_param[i][3][0])) + "-" + str(int(tab_param[i][3][1]))

            if (i+2 in effects[2]):
                emap += "#define_filter ft%d type=Wobble;mix=%d%%>%d%%;loFreq=%sHz;hiFreq=%sHz;Q=4.5;waveLength=%f\n" % (i, 0, mix, freq, freq, 1/8)
            allowed_filters[i] = False
        elif (fx_type == 12):
            # Sounds like high pass - replace it with bitcrusher which have a higher tone
            mix = float(effect[1])
            emap += "#define_fx %s type=BitCrusher;mix=%d%%>%d%%\n" % (name, 0, mix)
            name += ";5"
            # if (i+2 in effects[2]):
            #     emap += "#define_filter ft%d type=BitCrusher;mix=%d%%>%d%%;reduction=5samples\n" % (i, 0, mix)
        elif (fx_type == 0):
            # nofx
            pass
        else:
            print("Unknown FX: %d" % fx_type)

        fx_names[0][i] = name if left_name is None else left_name
        fx_names[1][i] = name if right_name is None else right_name
        fx_mix[name.split(";")[0]] = mix
        if (left_name is not None):
            fx_mix[left_name.split(";")[0]] = mix
        if (right_name is not None):
            fx_mix[right_name.split(";")[0]] = mix
    # States
    hold = [-1 for i in range(8)]
    fx_hold = [None for i in range(8)]
    fx_hostage = [None for i in range(8)]
    cur_filter = None
    hold_filter = 0
    # prev_filter = 0
    cur_gain = 90
    prev_bpm = None

    lane_hiding = False

    kmap = "--\n"
    vol_prev_pos = [None for i in range(8)]
    for measure in range(1, end[0]+1):
        beat_sig = current_beat(beats, measure)
        beat_step = (192 // beat_sig[1])
        measure_step = beat_sig[0] * beat_step

        # Empty measure
        if (measure not in measures):
            for bt in [2,3,4,5]:
                if hold[bt] > 0:
                    kmap+="2"
                    hold[bt] -= measure_step
                else:
                    kmap+="0"
            kmap += "|"
            for fx in [1,6]:
                if hold[fx] > 0:
                    kmap+="1"
                    hold[fx] -= measure_step
                else:
                    kmap+="0"
            kmap += "|"
            for vol in [0,7]:
                if hold[vol] > 0:
                    kmap+=":"
                else:
                    kmap+="-"
            if hold_filter > 0:
                hold_filter -= measure_step
            kmap += "\n--\n"
            continue


        total_notes = measures[measure]
        # if (total_notes > 192):
        #     print("WOW")
        #     # for safety
        #     total_notes = 192
        step = measure_step // total_notes

        for note in range(0, total_notes):
            cur = note * step
            beat = (cur // beat_step) + 1
            sub = cur % beat_step
            time = (measure, beat, sub)

            if time in beats:
                kmap+="beat=%d/%d\n" % beats[time]
            if time in bpms:
                if (prev_bpm != bpms[time][0]):
                    prev_bpm = bpms[time][0]
                    kmap+="t=%f\n" % bpms[time][0]
            if time in stop:
                kmap+="stop=%d\n" % (stop[time])

            note = ""
            # BT
            for bt in [2,3,4,5]:
                if hold[bt] > 0:
                    note+="2"
                    hold[bt] -= step
                elif time in tracks[bt]:
                    data = tracks[bt][time]
                    if data[0] > 0:
                        hold[bt] = data[0] - step
                        note+="2"
                    else:
                        note+="1"
                else:
                    note+="0"

            note += "|"

            # FX
            fx_collision = [None for i in range(8)]
            se_collision = [None for i in range(8)]
            se_count = 0
            for fx in [1,6]:
                if hold[fx] > 0:
                    note+="1"
                    hold[fx] -= step
                elif time in tracks[fx]:
                    data = tracks[fx][time]
                    if data[0] > 0:
                        hold[fx] = data[0] - step
                        if data[1] == 1 or data[1] == 254 or data[1] == -2:
                            # SwitchAudio
                            kmap+="fx-%s=FX_TRACK\n" % ("l" if fx == 1 else "r")
                        else:
                            fx_num = data[1] - 2
                            if (fx_num in fx_names[0 if fx == 1 else 1]):
                                fx_collision[fx] = fx_num
                                fx_hold[fx] = fx_num
                                kmap+="fx-%s=%s\n" % ("l" if fx == 1 else "r", fx_names[0 if fx == 1 else 1][fx_num])
                        note+="1"
                    else:
                        if data[1] > 0 and data[1] < 14:
                            fx_beats.add("%02d.ogg" % (data[1]+1))
                            se_collision[fx] = (
                                "l" if fx == 1 else "r",
                                "%02d.ogg" % (data[1]+1)
                            )
                            se_count += 1
                        note+="2"
                else:
                    other_lane = 7 - fx
                    if (fx_hostage[fx] is not None):
                        # release hostage fx
                        kmap+="fx:%s:mix=0%%>%d%%\n" % (fx_hostage[fx], fx_mix[fx_hostage[fx]])

                    if (fx_hostage[other_lane] is not None):
                        # release hostage fx
                        kmap+="fx:%s:mix=0%%>%d%%\n" % (fx_hostage[other_lane], fx_mix[fx_hostage[other_lane]])
                        fx_hostage[other_lane] = None

                    fx_hold[fx] = None
                    fx_hostage[fx] = None
                    note+="0"

            se_volume = FX_BEAT_VOLUME if se_count < 2 else FX_BEAT_VOLUME / 1.25
            for fx in [1,6]:
                if (se_collision[fx] is not None):
                    kmap+="fx-%s_se=%s;%d\n" % (se_collision[fx][0], se_collision[fx][1], se_volume)

                other_lane = 7 - fx
                if (fx_collision[fx] is not None):
                    if (fx_collision[other_lane] is not None):
                        if (fx == 6):
                            fx_hostage[fx] = fx_names[0 if other_lane == 1 else 1][fx_collision[other_lane]].split(";")[0]
                            if (fx_mix[fx_hostage[fx]] is not None):
                                kmap+="fx:%s:mix=0%%>0%%\n" % (fx_hostage[fx])
                            else:
                                fx_hostage[fx] = None
                    elif (fx_hold[other_lane] != None):
                            fx_hostage[fx] = fx_names[0 if other_lane == 1 else 1][fx_hold[other_lane]].split(";")[0]
                            if (fx_mix[fx_hostage[fx]] is not None):
                                kmap+="fx:%s:mix=0%%>0%%\n" % (fx_hostage[fx])
                            else:
                                fx_hostage[fx] = None


            note += "|"

            add_filter = None

            # VOL
            spin = ""
            for vol in [0,7]:
                if time in tracks[vol]:
                    data = tracks[vol][time]
                    filter_type = data[3]
                    # if (filter_type == 6):
                    #     if (cur_gain > 0):
                    #         kmap += "pfiltergain=0\n"
                    #         cur_gain = 0
                    # else:
                    #     if (cur_gain == 0):
                    #         kmap += "pfiltergain=90\n"
                    #         cur_gain = 90
                    #     if (cur_filter != filter_type):
                    #         if (filter_type >= 0 and filter_type < len(FILTER)):
                    #             kmap += "filtertype=%s\n" % FILTER[filter_type]

                    #         cur_filter = filter_type
                    if (hold_filter <= 0 and cur_filter != filter_type):
                        if (filter_type >= 0 and filter_type < len(FILTER)):
                            add_filter = "filtertype=%s\n" % FILTER[filter_type]
                            cur_filter = filter_type
                    
                    if (vol_prev_pos[vol] is None):
                        pos = int(round(data[0] / 127.0 * (len(VOL_CHAR) - 1)))
                    else:
                        if (abs(data[0] - vol_prev_pos[vol]) <= VOL_DRIFT_TOLERANCE):
                            pos = int(round(vol_prev_pos[vol] / 127.0 * (len(VOL_CHAR) - 1)))
                        else:
                            pos = int(round(data[0] / 127.0 * (len(VOL_CHAR) - 1)))

                    vol_prev_pos[vol] = data[0]

                    if data[1] == 1:
                        if (data[4]):
                            kmap+="laserrange_" + ("l" if vol == 0 else "r") + "=2x\n"
                        hold[vol] = 1
                    if data[1] == 2:
                        hold[vol] = -1

                    if (data[6]):
                        # is ghost
                        note += ":"
                    else:
                        note += VOL_CHAR[pos]

                    # try Spin Effect if not yet
                    if (len(spin) == 0 and data[2] > 0):
                        # try get slam
                        slam_time, _ = advance_time(time, 6, beats)
                        spin_left = None
                        if (slam_time in tracks[vol]):
                            spin_left = tracks[vol][slam_time][0] < data[0]
                        if (spin_left is not None):
                            if (data[2] == 1):
                                spin += "@%s192" % ("(" if spin_left else ")")
                            elif (data[2] == 2):
                                spin += "@%s48" % ("(" if spin_left else ")")
                            elif (data[2] == 3):
                                spin += "@%s96" % ("(" if spin_left else ")")
                            elif (data[2] == 4):
                                spin += "@%s432" % ("(" if spin_left else ")")
                                # special case: spin 4, 2.75 round
                                ex_time, ex_note = advance_time(time, 480, beats)

                                # for usc
                                usc_time, usc_note = advance_time(ex_time, 12, beats)

                                # don't really care about special camera, assume spinning from 0 position
                                if (time in camera[2]):
                                    camera[2][time].append(0)
                                else:
                                    camera[2][time] = [0]

                                if (ex_time in camera[2]):
                                    camera[2][ex_time].append((720 / TILT_FACTOR) if spin_left else (-720 / TILT_FACTOR))
                                    camera[2][ex_time].append(0)
                                else:
                                    camera[2][ex_time] = [(720 / TILT_FACTOR) if spin_left else (-720 / TILT_FACTOR), 0]

                                if (usc_time in camera[2]):
                                    camera[2][usc_time].append("normal")
                                else:
                                    camera[2][usc_time] = ["normal"]

                                ex_measure = ex_time[0]
                                if (ex_measure not in measures):
                                    measures[ex_measure] = ex_note
                                else:
                                    measures[ex_measure] = lcm(measures[ex_measure], ex_note)

                                usc_measure = usc_time[0]
                                if (usc_measure not in measures):
                                    measures[usc_measure] = usc_note
                                else:
                                    measures[usc_measure] = lcm(measures[usc_measure], usc_note)

                            elif (data[2] == 5):
                                spin += "@%s96" % ("<" if spin_left else ">")
                            elif (data[2] > 5):
                                print("Unknown spin effect: %d" % (data[2]))
                elif hold[vol] > 0:
                    note += ":"
                else:
                    note += "-"

            # AUTO TAB
            if (hold_filter > 0):
                hold_filter -= step

            if (time in custom_filter):
                filter_num, filter_duration = custom_filter[time]
                filter_num -= 2
                if (filter_num in allowed_filters):
                    add_filter = "filtertype=ft%d\n" % (filter_num)
                    if (allowed_filters[filter_num]):
                        add_filter += "filter:ft%d:updateTrigger=on\n" % (filter_num)
                    hold_filter = filter_duration - step
                    # prev_filter = cur_filter
                    cur_filter = -1

            if (add_filter is not None):
                kmap += add_filter

            # SP
            sps = [
                ("zoom_top", camera[0], lambda x: camera_transpose(x)),
                ("zoom_bottom", camera[1], lambda x: -(x-60.12)*2.6),
                ("tilt", camera[2], lambda x: x),
            ]

            for cam in sps:
                op_name, target, translate = cam
                if (time in target):
                    prev_pos = None
                    if (time == (1,1,0)):
                        pos = target[time][-1]
                        if (type(pos) == str):
                            kmap += "%s=%s\n" % (op_name, pos)
                        else:
                            kmap += "%s=%.2f\n" % (op_name, translate(pos))
                        prev_pos = pos
                    else:
                        for pos in target[time]:
                            if (pos == prev_pos):
                                continue
                            if (type(pos) == str):
                                kmap += "%s=%s\n" % (op_name, pos)
                            else:
                                kmap += "%s=%.2f\n" % (op_name, translate(pos))
                            prev_pos = pos

            # lane_toggle
            if (time in camera[3]):
                for toggle in camera[3][time]:
                    toggle_dur, toggle_state = toggle
                    if (toggle_state != lane_hiding):
                        kmap += "lane_toggle=%d\n" % (toggle_dur)
                        lane_hiding = toggle_state

            # finally add the note itself
            kmap += note+spin+"\n"
        kmap += "--\n"

    kmap += emap
    kmap += "#define_filter nof type=Gate;mix=0%>0%;rate=100%;waveLength=2\n"
    kmap += "#define_filter lbic type=BitCrusher;reduction=0samples-10samples\n"
    return kmap, fx_beats

def vox2ksh(filename, fx = None):
    return map2kshbeats(readvox(filename), fx)

if (__name__ == "__main__"):
    path = sys.argv[1]
    target = sys.argv[2]

    with open(target, 'w', encoding="utf-8-sig") as f:
        f.write(vox2ksh(path)[0])
