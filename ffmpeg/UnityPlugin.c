#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavformat/avio.h>
#include <libswresample/swresample.h>
#include <libswscale/swscale.h>
#include <libavutil/opt.h>

#include <SDL.h>
#include <SDL_thread.h>

#ifdef __MINGW32__
#undef main /* Prevents SDL from overriding main() */
#endif

#include <stdio.h>
#include <assert.h>
#include <math.h>

// compatibility with newer API
#if LIBAVCODEC_VERSION_INT < AV_VERSION_INT(55,28,1)
#define av_frame_alloc avcodec_alloc_frame
#define av_frame_free avcodec_free_frame
#endif

#define SDL_AUDIO_BUFFER_SIZE 1024
#define MAX_AUDIO_FRAME_SIZE 192000
#define MAX_AUDIOQ_SIZE (5 * 16 * 1024)
#define MAX_VIDEOQ_SIZE (5 * 256 * 1024)
#define AV_SYNC_THRESHOLD 0.01
#define AV_NOSYNC_THRESHOLD 10.0
#define SAMPLE_CORRECTION_PERCENT_MAX 10
#define AUDIO_DIFF_AVG_NB 20
#define FF_ALLOC_EVENT   (SDL_USEREVENT)
#define FF_REFRESH_EVENT (SDL_USEREVENT + 1)
#define FF_QUIT_EVENT (SDL_USEREVENT + 2)
#define VIDEO_PICTURE_QUEUE_SIZE 1
#define DEFAULT_AV_SYNC_TYPE AV_SYNC_VIDEO_MASTER

enum 
{
    AV_SYNC_AUDIO_MASTER,
    AV_SYNC_VIDEO_MASTER,
    AV_SYNC_EXTERNAL_MASTER,
};

#define DEFAULT_AV_SYNC_TYPE AV_SYNC_VIDEO_MASTER

typedef struct PacketQueue
{
    AVPacketList *first_pkt, *last_pkt;
    int nb_packets;
    int size;
    SDL_mutex *mutex;
    SDL_cond *cond;
} PacketQueue;


typedef struct VideoPicture
{
    SDL_Overlay *bmp;
    int width, height; /* source height & width */
} VideoPicture;

typedef struct VideoState
{
    AVFormatContext *pFormatCtx;
    int             videoStream;

    AVStream        *video_st;
    PacketQueue     videoq;

    VideoPicture    pictq;
    int             pictq_size;

    SDL_Thread      *video_tid;
    SDL_Thread      *parse_tid;

    char            filename[1024];
    int             quit;

    AVIOContext     *io_context;
    struct SwsContext *sws_ctx;
} VideoState;

SDL_Surface     *screen;

/* Since we only have one decoding thread, the Big Struct
   can be global in case we need it. */
VideoState *global_video_state;

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


static int packet_queue_get(PacketQueue *q, AVPacket *pkt, int block)
{
    AVPacketList *pkt1;
    int ret;
    
    SDL_LockMutex(q->mutex);
    for(;;)
    {
        if(global_video_state->quit)
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
        else if(!block)
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


void video_display(VideoState *is)
{

    SDL_Rect rect;
    VideoPicture *vp;
    float aspect_ratio;
    int w, h, x, y;
    int i;

    vp = &is->pictq;
    if(vp->bmp)
    {
        if(is->video_st->codec->sample_aspect_ratio.num == 0)
        {
            aspect_ratio = 0;
        } else
        {
            aspect_ratio = av_q2d(is->video_st->codec->sample_aspect_ratio) *
                is->video_st->codec->width / is->video_st->codec->height;
        }
        if(aspect_ratio <= 0.0)
        {
            aspect_ratio = (float)is->video_st->codec->width /
                (float)is->video_st->codec->height;
        }
        h = screen->h;
        w = ((int)rint(h * aspect_ratio)) & -3;
        if(w > screen->w)
        {
            w = screen->w;
            h = ((int)rint(w / aspect_ratio)) & -3;
        }
        x = (screen->w - w) / 2;
        y = (screen->h - h) / 2;

        rect.x = x;
        rect.y = y;
        rect.w = w;
        rect.h = h;
        SDL_DisplayYUVOverlay(vp->bmp, &rect);
    }
}

void alloc_picture(void *userdata)
{
    VideoState *is = (VideoState *)userdata;
    VideoPicture *vp;

    vp = &is->pictq;
    if(vp->bmp)
    {
        // we already have one make another, bigger/smaller
        SDL_FreeYUVOverlay(vp->bmp);
    }
    // Allocate a place to put our YUV image on that screen
    vp->bmp = SDL_CreateYUVOverlay(is->video_st->codec->width,
            is->video_st->codec->height,
            SDL_YV12_OVERLAY,
            screen);

    vp->width = is->video_st->codec->width;
    vp->height = is->video_st->codec->height;

}

int init_picture(VideoState *is, AVFrame *pFrame)
{
    VideoPicture *vp;
    AVPicture pict;

    if(is->quit)
        return -1;

    vp = &is->pictq;

    /* allocate or resize the buffer! */
    if(!vp->bmp ||
            vp->width != is->video_st->codec->width ||
            vp->height != is->video_st->codec->height)
    {
        alloc_picture(is);
        if(is->quit)
        {
            return -1;
        }
    }
    /* We have a place to put our picture on the queue */
    if(vp->bmp)
    {
        SDL_LockYUVOverlay(vp->bmp);

        /* point pict at the queue */
        pict.data[0] = vp->bmp->pixels[0];
        pict.data[1] = vp->bmp->pixels[2];
        pict.data[2] = vp->bmp->pixels[1];
        pict.linesize[0] = vp->bmp->pitches[0];
        pict.linesize[1] = vp->bmp->pitches[2];
        pict.linesize[2] = vp->bmp->pitches[1];

        // Convert the image into YUV format that SDL uses
        sws_scale(
                is->sws_ctx, 
                (uint8_t const * const *)pFrame->data, 
                pFrame->linesize, 
                0, 
                is->video_st->codec->height, 
                pict.data, 
                pict.linesize
                );
        SDL_UnlockYUVOverlay(vp->bmp);
        video_display(is);
    }
    return 0;
}

int video_thread(void *arg)
{
    VideoState *is = (VideoState *)arg;
    AVPacket pkt1, *packet = &pkt1;
    int frameFinished;
    AVFrame *pFrame;

    pFrame = av_frame_alloc();

    for(;;)
    {
        if(packet_queue_get(&is->videoq, packet, 1) < 0)
        {
            // means we quit getting packets
            break;
        }
        // Decode video frame
        avcodec_decode_video2(is->video_st->codec, pFrame, &frameFinished, packet);

        // Did we get a video frame?
        if(frameFinished)
        {
            if(init_picture(is, pFrame) < 0)
                break;
        }
        av_free_packet(packet);
    }
    av_frame_free(&pFrame);
    return 0;
}

int stream_component_open(VideoState *is, int stream_index)
{

    AVFormatContext *pFormatCtx = is->pFormatCtx;
    AVCodecContext *codecCtx = NULL;

    AVCodec *codec = NULL;
    AVDictionary *optionsDict = NULL;

    if(stream_index < 0 || stream_index >= pFormatCtx->nb_streams)
    {
        return -1;
    }

    codecCtx = pFormatCtx->streams[stream_index]->codec;
    codec = avcodec_find_decoder(codecCtx->codec_id);

    if(!codec || avcodec_open2(codecCtx, codec, &optionsDict) < 0)
    {
        fprintf(stdout, "Unsupported codec!\n");
        return -1;
    }

    if(codecCtx->codec_type == AVMEDIA_TYPE_VIDEO)
    {
        is->videoStream = stream_index;
        is->video_st = pFormatCtx->streams[stream_index];

        packet_queue_init(&is->videoq);
        is->video_tid = SDL_CreateThread(video_thread, is);
        is->sws_ctx = sws_getContext
            (
             is->video_st->codec->width,
             is->video_st->codec->height,
             is->video_st->codec->pix_fmt,
             is->video_st->codec->width,
             is->video_st->codec->height,
             PIX_FMT_YUV420P,
             SWS_BILINEAR,
             NULL,
             NULL,
             NULL
            );
    }
    return 0;
}


int decode_interrupt_cb(void *opaque)
{
    return (global_video_state && global_video_state->quit);
}


int decode_thread(void *arg)
{
    VideoState *is = (VideoState *)arg;
    AVFormatContext *pFormatCtx = NULL;
    AVPacket pkt1, *packet = &pkt1;

    AVIOInterruptCB callback;

    int video_index = -1;
    int audio_index = -1;
    int i;

    is->videoStream=-1;

    global_video_state = is;
    // Will interrupt blocking functions ifwe quit!
    callback.callback = decode_interrupt_cb;
    callback.opaque = is;

    if(avio_open2(&is->io_context, is->filename, 0, &callback, NULL) < 0)
    {
        fprintf(stdout, "Unable to open I/O for %s\n", is->filename);
        return -1;
    }

    // Open video file
    if(avformat_open_input(&pFormatCtx, is->filename, NULL, NULL)!=0)
    {
        fprintf(stdout, "Couldn't Open file\n");
        return -1; // Couldn't open file
    }

    is->pFormatCtx = pFormatCtx;

    // Retrieve stream information
    if(avformat_find_stream_info(pFormatCtx, NULL)<0)
    {
        fprintf(stdout, "Couldn't Retrieve stream information\n");
        return -1; // Couldn't find stream information
    }

    // Dump information about file onto standard error
    av_dump_format(pFormatCtx, 0, is->filename, 0);

    // Find the first video stream
    for(i=0; i<pFormatCtx->nb_streams; i++)
    {
        if(pFormatCtx->streams[i]->codec->codec_type==AVMEDIA_TYPE_VIDEO &&
                video_index < 0)
        {
            video_index=i;
            break;
        }
    }
    if(video_index == -1)
    {
        fprintf(stdout, "Couldn't find video stream\n");
        return -1;
    }
    stream_component_open(is, video_index);

    // main decode loop
    for(;;)
    {
        if(is->quit)
        {
            break;
        }
        if(av_read_frame(is->pFormatCtx, packet) < 0)
        {
            if(is->pFormatCtx->pb->error == 0)
                continue;
            else
                break;
        }
        if(packet->stream_index == is->videoStream)
            packet_queue_put(&is->videoq, packet);
        else
            av_free_packet(packet);
    }
    return 0;
}

int main(int argc, char *argv[])
{
    SDL_Event       event;
    VideoState      *is;
    is = av_mallocz(sizeof(VideoState));

    if(argc < 2)
    {
        fprintf(stdout, "Usage: test <file>\n");
        exit(1);
    }
    // Register all formats and codecs
    av_register_all();
    avformat_network_init();

    if(SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER))
    {
        fprintf(stdout, "Could not initialize SDL - %s\n", SDL_GetError());
        exit(1);
    }

    // Make a screen to put our video
#ifndef __DARWIN__
    screen = SDL_SetVideoMode(640, 480, 0, 0);
#else
    screen = SDL_SetVideoMode(640, 480, 24, 0);
#endif
    if(!screen)
    {
        fprintf(stdout, "SDL: could not set video mode - exiting\n");
        exit(1);
    }

    av_strlcpy(is->filename, argv[1], sizeof(is->filename));

    is->parse_tid = SDL_CreateThread(decode_thread, is);
    if(!is->parse_tid)
    {
        av_free(is);
        return -1;
    }
    for(;;)
    {
        SDL_WaitEvent(&event);
        switch(event.type)
        {
            case FF_QUIT_EVENT:
            case SDL_QUIT:
                is->quit = 1;
                SDL_Quit();
                exit(0);
                break;
            default:
                break;
        }
    }
    
    return 0;
}
