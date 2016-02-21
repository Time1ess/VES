// A pedagogical video player that will stream through every video frame as fast as it can
// // and play audio (out of sync).
// //
// //
// // Use
// //
// // gcc `pkg-config --cflags --libs libavutil libavformat libavcodec 
// //     libswscale` `sdl-config --cflags --libs` -o tutorial03 tutorial03.c
// // to build (assuming libavformat and libavcodec are correctly installed, 
// // and assuming you have sdl-config. Please refer to SDL docs for your installation.)
// //
// // Run using
// // tutorial03 myvideofile.mpg
// //
// // to play the stream on your screen.
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libswscale/swscale.h>
#include <SDL.h>
#include <SDL_thread.h>
#include <stdio.h>
#include <assert.h>

#define SDL_AUDIO_BUFFER_SIZE 1024
#define MAX_AUDIO_FRAME_SIZE 192000


typedef struct PacketQueue
{
    AVPacketList *first_pkt, *last_pkt;
    int nb_packets;
    int size;
    SDL_mutex *mutex;
    SDL_cond *cond;
} PacketQueue;

PacketQueue audioq;

void packet_queue_init(PacketQueue *q)
{
    memset(q, 0, sizeof(PacketQueue));
    q->mutex = SDL_CreateMutex();
    q->cond = SDL_CreateCond();
}

int packet_queue_put(PacketQueue *q, AVPacket *pkt)
{
    AVPacketList *pkt1;
    if(av_dup_packet(pkt) < 0)
    {
        return -1;
    }

    pkt1 = av_malloc(sizeof(AVPacketList));
    if(!pkt1)
        return -1;
    pkt1->pkt = *pkt;
    pkt1->next = NULL;

    SDL_LockMutex(q->mutex);

    if(!q->last_pkt)
        q->first_pkt = pkt1;
    else
        q->last_pkt->next = pkt1;
    q->last_pkt = pkt1;
    q->nb_packets++;
    q->size += pkt1->pkt.size;
    SDL_CondSignal(q->cond);

    SDL_UnlockMutex(q->mutex);
    return 0;
}

int quit = 0;

static int packet_queue_get(PacketQueue *q, AVPacket *pkt, int block)
{
    AVPacketList *pkt1;
    int ret;

    SDL_LockMutex(q->mutex);

    for(;;)
    {
        if(quit)
        {
            ret = -1;
            break;
        }
        
        pkt1 = q->first_pkt;
        if(pkt1)
        {
            q->first_pkt = pkt1->next;
            if(!q->first_pkt)
                q->last_pkt = NULL;
            q->nb_packets--;
            q->size -= pkt1->pkt.size;
            *pkt = pkt1->pkt;
            av_free(pkt1);
            ret = 1;
            break;
        }
        else if (!block)
        {
            ret = 0;
            break;
        }
        else
        {
            SDL_CondWait(q->cond, q->mutex);
        }
    }
    SDL_UnlockMutex(q->mutex);
    return ret;
}

int audio_decode_frame(AVCodecContext *aCodecCtx, uint8_t *audio_buf,
        int buf_size)
{
    static AVPacket pkt;
    static int audio_pkt_size = 0;
    static AVFrame frame;

    int len1, data_size= 0;

    for(;;)
    {
        while(audio_pkt_size > 0)
        {
            int got_frame = 0;
            len1 = avcodec_decode_audio4(aCodecCtx, &frame, &got_frame, &pkt);
            if(len1 < 0)
            {
                /* If error, skip frame */
                audio_pkt_size = 0;
                break;
            }
            audio_pkt_size -= len1;
            data_size = 0;
            if(got_frame)
            {
                data_size = av_samples_get_buffer_size(NULL,
                        aCodecCtx->channels,
                        frame.nb_samples,
                        aCodecCtx->sample_fmt,
                        1);
                assert(data_size <= buf_size);
                memcpy(audio_buf, frame.data[0], data_size);
            }
            if(data_size <= 0)
            {
                /* No data yet, get more frames */
                continue;
            }
            return data_size;
        }
        if(pkt.data)
            av_free_packet(&pkt);

        if(quit)
        {
            return -1;
        }

        if(packet_queue_get(&audioq, &pkt, 1) < 0)
        {
            return -1;
        }
        audio_pkt_size = pkt.size;
    }
}

void audio_callback(void *userdata, Uint8 *stream, int len)
{
    AVCodecContext *aCodecCtx = (AVCodecContext *)userdata;
    int len1, audio_size;

    static uint8_t audio_buf[(MAX_AUDIO_FRAME_SIZE * 3) / 2];
    static unsigned int audio_buf_size = 0;
    static unsigned int audio_buf_index = 0;

    while(len > 0)
    {
        if(audio_buf_index >= audio_buf_size)
        {
            /* We have already sent all our data; get more */
            audio_size = audio_decode_frame(aCodecCtx, audio_buf,
                    sizeof(audio_buf));

            if(audio_size < 0)
            {
                /* If error, output silence */
                audio_buf_size = 1024;
                memset(audio_buf, 0, audio_buf_size);
            }
            else
            {
                audio_buf_size = audio_size;
            }
            audio_buf_index = 0;
        }
        len1 = audio_buf_size - audio_buf_index;
        if(len1 > len)
            len1 = len;
        memcpy(stream, (uint8_t *)audio_buf + audio_buf_index, len1);
        len -= len1;
        stream += len1;
        audio_buf_index += len1;
    }
}
                

int main(int argc,char *argv[])
{
    av_register_all();  // Register all available file formats and codecs with the library
    if(SDL_Init(SDL_INIT_VIDEO|SDL_INIT_AUDIO|SDL_INIT_TIMER))
    {
        fprintf(stderr, "Could not initialize SDL - %s\n", SDL_GetError());
        exit(1);
    }

    AVFormatContext *pFormatCtx = NULL;

    // Open video file
    if(avformat_open_input(&pFormatCtx, argv[1], NULL, NULL) != 0)
    {
        fprintf(stderr, "Couldn't open the file!\n");
        return -1;
    }

    // Retrieve stream information
    if(avformat_find_stream_info(pFormatCtx, NULL) < 0)
    {
        fprintf(stderr, "Couldn't find stream information!\n");
        return -1;  // Couldn't find stream information
    }

    // Dump information about file onto standard error
    av_dump_format(pFormatCtx, 0, argv[1], 0);

    int i;
    AVCodecContext *pCodecCtxOrig = NULL;
    AVCodecContext *pCodecCtx = NULL;
    AVCodecContext *aCodecCtxOrig = NULL;
    AVCodecContext *aCodecCtx = NULL;

    // Find the first video stream
    int audioStream = -1;
    int videoStream = -1;
    for(i=0; i < pFormatCtx->nb_streams; i++)
    {
        if(pFormatCtx->streams[i]->codec->codec_type == AVMEDIA_TYPE_VIDEO
                && videoStream < 0)
        {
            videoStream = i;
        }
        if(pFormatCtx->streams[i]->codec->codec_type == AVMEDIA_TYPE_AUDIO
                && audioStream < 0)
        {
            audioStream = i;
        }
    }
    
    if(videoStream == -1 || audioStream == -1)
    {
        fprintf(stderr, "Didn't find a video or audio stream!\n");
        return -1;  // Didn't find a video stream
    }

    // Get a pointer to the codec context for the video stream and audio stream
    pCodecCtxOrig = pFormatCtx->streams[videoStream]->codec;
    aCodecCtxOrig = pFormatCtx->streams[audioStream]->codec;

    AVCodec *pCodec = NULL;
    AVCodec *aCodec = NULL;

    // Find the decoder for the video stream
    pCodec = avcodec_find_decoder(pCodecCtxOrig->codec_id);
    if(pCodec == NULL)
    {
        fprintf(stderr, "Unsupported codec!\n");
        return -1;
    }
    aCodec = avcodec_find_decoder(aCodecCtxOrig->codec_id);
    if(aCodec == NULL)
    {
        fprintf(stderr, "Unsupported codec!\n");
        return -1;
    }
    // Copy context
    pCodecCtx = avcodec_alloc_context3(pCodec);
    aCodecCtx = avcodec_alloc_context3(aCodec);

    if(avcodec_copy_context(pCodecCtx, pCodecCtxOrig) != 0)
    {
        fprintf(stderr, "Couldn't copy codec context");
        return -1;  // Error copying codec context
    }
    if(avcodec_copy_context(aCodecCtx, aCodecCtxOrig) != 0)
    {
        fprintf(stderr, "Couldn't copy codec context");
        return -1;
    }

    // Open codec
    if(avcodec_open2(pCodecCtx, pCodec, NULL) < 0)
    {
        fprintf(stderr, "Couldn't open codec!\n");
        return -1;  // Could not open codec
    }

    SDL_AudioSpec wanted_spec, spec;

    // Set audio settings from codec info
    wanted_spec.freq = aCodecCtx->sample_rate;
    wanted_spec.format = AUDIO_S16SYS;
    wanted_spec.channels = aCodecCtx->channels;
    wanted_spec.silence = 0;
    wanted_spec.samples = SDL_AUDIO_BUFFER_SIZE;
    wanted_spec.callback = audio_callback;
    wanted_spec.userdata = aCodecCtx;

    if(SDL_OpenAudio(&wanted_spec, &spec) < 0)
    {
        fprintf(stderr, "SDL_OpenAudio: %s\n", SDL_GetError());
        return -1;
    }

    if(avcodec_open2(aCodecCtx, aCodec, NULL) < 0)
    {
        fprintf(stderr, "Couldn't open codec!\n");
        return -1;
    }

    packet_queue_init(&audioq);
    SDL_PauseAudio(0);


    AVFrame *pFrame = NULL;
    AVFrame *pFrameRGB = NULL;

    // Allocate video frame
    pFrame = av_frame_alloc();
    if(pFrame == NULL)
    {
        fprintf(stderr, "Couldn't allocate pFrame!\n");
        return -1;
    }
    // Allocate an AVFrame structure
    pFrameRGB = av_frame_alloc();
    if(pFrameRGB == NULL)
    {
        fprintf(stderr, "Couldn't allocate pFrameRGB!\n");
        return -1;
    }

    uint8_t *buffer = NULL;
    int numBytes;
    // Determine required buffer size and allocate buffer
    numBytes = avpicture_get_size(PIX_FMT_RGB24,pCodecCtx->width,
            pCodecCtx->height);
    buffer = (uint8_t *)av_malloc(numBytes*sizeof(uint8_t));

    // Assign appropriate parts of buffer to image planes in pFrameRGB
    // Note that pFrameRGB is an AVFrame, but AVFrame is a superset
    // of AVPicture
    avpicture_fill((AVPicture *)pFrameRGB, buffer, PIX_FMT_RGB24,
            pCodecCtx->width, pCodecCtx->height);

    int frameFinished;
    AVPacket packet;

    SDL_Surface *screen;

#ifndef __DARWIN__
    screen = SDL_SetVideoMode(pCodecCtx->width, pCodecCtx->height, 0, 0);
#else
    screen = SDL_SetVideoMode(pCodecCtx->width, pCodecCtx->height, 24, 0);
#endif
    if(!screen)
    {
        fprintf(stderr, "SDL: could not set video mode - exiting\n");
        exit(1);
    }

    SDL_Overlay *bmp = NULL;
    struct SwsContext *sws_ctx = NULL;

    bmp = SDL_CreateYUVOverlay(pCodecCtx->width,pCodecCtx->height,
            SDL_YV12_OVERLAY, screen);

    // Initialize SWS context for softscaling
    sws_ctx = sws_getContext(pCodecCtx->width,
            pCodecCtx->height,
            pCodecCtx->pix_fmt,
            pCodecCtx->width,
            pCodecCtx->height,
            PIX_FMT_YUV420P,
            SWS_BILINEAR,
            NULL,
            NULL,
            NULL
            );

    i = 0;

    while(av_read_frame(pFormatCtx, &packet) >= 0)
    {
        // Is this a packet from the video stream?
        if(packet.stream_index == videoStream)
        {
            // Decode video frame
            avcodec_decode_video2(pCodecCtx, pFrame, &frameFinished, &packet);

            SDL_Rect rect;

            // Did we get a video frame?
            if(frameFinished)
            {
                SDL_LockYUVOverlay(bmp);

                AVPicture pict;
                pict.data[0] = bmp->pixels[0];
                pict.data[1] = bmp->pixels[2];
                pict.data[2] = bmp->pixels[1];

                pict.linesize[0] = bmp->pitches[0];
                pict.linesize[1] = bmp->pitches[2];
                pict.linesize[2] = bmp->pitches[1];
                // Convert the image into YUV format that SDL uses
                sws_scale(sws_ctx, (uint8_t const * const *)pFrame->data,
                        pFrame->linesize, 0, pCodecCtx->height,
                        pict.data, pict.linesize);

                SDL_UnlockYUVOverlay(bmp);
                rect.x = 0;
                rect.y = 0;
                rect.w = pCodecCtx->width;
                rect.h = pCodecCtx->height;
                SDL_DisplayYUVOverlay(bmp, &rect);
            }
        }
        else if(packet.stream_index == audioStream)
        {
            packet_queue_put(&audioq, &packet);
        }
        else
        {
            av_free_packet(&packet);
        }

        SDL_Event event;

        // Free the packet that was allocated by av_read_frame
        SDL_PollEvent(&event);
        switch(event.type)
        {
            case SDL_QUIT:
                quit = 1;
                SDL_Quit();
                exit(0);
                break;
            default:
                break;
        }
    }

    // Free the RGB image
    av_free(buffer);
    av_free(pFrameRGB);

    // Free the YUV frame
    av_free(pFrame);

    // Close the codecs
    avcodec_close(pCodecCtx);
    avcodec_close(pCodecCtxOrig);

    // Close the video file
    avformat_close_input(&pFormatCtx);

    return 0;
}
