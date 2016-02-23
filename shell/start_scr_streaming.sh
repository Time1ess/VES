ffmpeg \
    -f avfoundation -i "1" -s 640*480 -r 29.97 \
    -c:v mpeg2video -q:v 2 -pix_fmt yuv420p -g 1 -threads 4\
    -f mpegts udp://127.0.0.1:6666
    # -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv444p \
    # -x264opts crf=20:vbv-maxrate=3000:vbv-bufsize=100:intra-refresh=1:slice-max-size=1500:keyint=30:ref=1 \
