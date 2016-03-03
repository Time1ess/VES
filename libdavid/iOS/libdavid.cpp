#include "libdavid.h"


/* Since we only have one decoding thread, the Big Struct
 can be global in case we need it. */
VideoState *gs;
AVFrame *pFrameRGB = av_frame_alloc();
pthread_cond_t event_cond = PTHREAD_COND_INITIALIZER;
pthread_mutex_t event_mutex = PTHREAD_MUTEX_INITIALIZER;
int event_type = 0;


void packet_queue_init(PacketQueue *q)
{
    memset(q, 0, sizeof(PacketQueue));
    q->mutex = PTHREAD_MUTEX_INITIALIZER;
    q->cond = PTHREAD_COND_INITIALIZER;
}


int packet_queue_put(PacketQueue *q, AVPacket *pkt)
{
    
    AVPacketList *pkt1;
    if(av_dup_packet(pkt) < 0)
    {
        return -1;
    }
    pkt1 = (AVPacketList *)av_malloc(sizeof(AVPacketList));
    if(!pkt1)
        return -1;
    pkt1->pkt = *pkt;
    pkt1->next = NULL;
    
    pthread_mutex_lock(&q->mutex);
    
    if(!q->last_pkt)
        q->first_pkt = pkt1;
    else
        q->last_pkt->next = pkt1;
    q->last_pkt = pkt1;
    q->nb_packets++;
    q->size += pkt1->pkt.size;

    pthread_cond_signal(&q->cond);
    pthread_mutex_unlock(&q->mutex);
    return 0;
}


static int packet_queue_get(PacketQueue *q, AVPacket *pkt, int block)
{
    AVPacketList *pkt1;
    int ret;
    
    pthread_mutex_lock(&q->mutex);
    for(;;)
    {
        if(gs->quit)
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
            pthread_cond_wait(&q->cond, &q->mutex);
        }
    }
    pthread_mutex_unlock(&q->mutex);
    return ret;
}


int init_picture(VideoState *is, AVFrame *pFrame)
{
 
    if(is->quit||pFrameRGB == NULL)
        return -1;
    
    sws_scale(
              is->sws_ctx,
              (uint8_t const * const *)pFrame->data,
              pFrame->linesize,
              0,
              is->video_st->codec->height,
              pFrameRGB->data,
              pFrameRGB->linesize
              );
    return 0;
}

void *video_thread(void *arg)
{
    VideoState *is = (VideoState *)arg;
    AVPacket pkt1, *packet = &pkt1;
    int frameFinished;
    AVFrame *pFrame;
    
    pFrame = av_frame_alloc();
    
    for(;;)
    {
        if(is->quit)
        {
            break;
        }
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
            init_picture(is, pFrame);
        }
        av_free_packet(packet);
    }
    av_frame_free(&pFrame);
    return NULL;
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
        is->sws_ctx = sws_getContext
        (
         is->video_st->codec->width,
         is->video_st->codec->height,
         is->video_st->codec->pix_fmt,
         VIEW_WIDTH,
         VIEW_HEIGHT,
         AV_PIX_FMT_RGBA,
         SWS_BILINEAR,
         NULL,
         NULL,
         NULL
         );
        //fprintf(stdout, "create video thread\n");
        pthread_create(&is->video_tid, NULL, video_thread, is);
    }
    return 0;
}


int decode_interrupt_cb(void *opaque)
{
    return (gs && gs->quit);
}


void *decode_thread(void *arg)
{
    VideoState *is = (VideoState *)arg;
    AVFormatContext *pFormatCtx = NULL;
    AVPacket pkt1, *packet = &pkt1;
    
    AVIOInterruptCB callback;
    
    int video_index = -1;
    int i;
    
    is->videoStream=-1;
    
    gs = is;
    // Will interrupt blocking functions ifwe quit!
    callback.callback = decode_interrupt_cb;
    callback.opaque = is;
    
    if(avio_open2(&is->io_context, is->filename, 0, &callback, NULL) < 0)
    {
        fprintf(stdout, "Unable to open I/O for file\n");
        return NULL;
    }
    //fprintf(stdout, "avio_open2 done\n");
    
    // Open video file
    if(avformat_open_input(&pFormatCtx, is->filename, NULL, NULL)!=0)
    {
        fprintf(stdout, "Couldn't Open file\n");
        return NULL; // Couldn't open file
    }
    //fprintf(stdout, "open_input done\n");
    
    is->pFormatCtx = pFormatCtx;
    
    // Retrieve stream information
    if(avformat_find_stream_info(pFormatCtx, NULL)<0)
    {
        fprintf(stdout, "Couldn't Retrieve stream information\n");
        return NULL; // Couldn't find stream information
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
        return NULL;
    }
    //fprintf(stdout, "stream component open\n");
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
    return NULL;
}

extern "C" int UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API init(char* name, int textureId)
{
//    SDL_Event       event;

    VideoState      *is;
    is = (VideoState*)av_mallocz(sizeof(VideoState));
    if(name == NULL) return -1;

    
    // Register all formats and codecs
    av_register_all();
    avformat_network_init();
    
    uint8_t *buffer;
    int buffer_size;
    buffer_size = avpicture_get_size(AV_PIX_FMT_RGBA, VIEW_WIDTH, VIEW_HEIGHT);

    buffer = (uint8_t *) av_malloc(buffer_size*sizeof(uint8_t));
    
    avpicture_fill((AVPicture *) pFrameRGB, buffer, AV_PIX_FMT_RGBA,
                   VIEW_WIDTH, VIEW_HEIGHT);
    

    strcpy(is->filename, name);
    is->textureId = textureId;
    pthread_create(&is->parse_tid, NULL, decode_thread, is);
    if(!is->parse_tid)
    {
        av_free(is);
        return -1;
    }
    int ret = 0;
    for(;;)
    {
//        SDL_WaitEvent(&event);
        pthread_mutex_lock(&event_mutex);
        pthread_cond_wait(&event_cond, &event_mutex);
        switch(event_type)
        {
            case FF_QUIT_EVENT:
                ret = pthread_join(is->parse_tid, NULL);
                if(ret)
                    fprintf(stdout, "decode_thread exit error.\n");
                ret = pthread_join(is->video_tid, NULL);
                if(ret)
                    fprintf(stdout, "video thread exit error.\n");
                av_frame_free(&pFrameRGB);
                return 0;
                break;
            default:
                break;
        }
        pthread_mutex_unlock(&event_mutex);
    }
    av_frame_free(&pFrameRGB);
    return 0;
}


//extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API destroy(void *arg)
//{
//    VideoState *is = (VideoState *)arg;
//    av_free(is);
//}

extern "C" int UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API dlltest()
{
    sleep(3);
    return 100;
}

extern "C" int UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API terminate()
{
    gs->quit = 1;
    pthread_mutex_lock(&event_mutex);
    event_type = FF_QUIT_EVENT;
    pthread_mutex_unlock(&event_mutex);
    return 1;
}

static void UNITY_INTERFACE_API OnRenderEvent(int texID)
{
    GLuint gltex = (GLuint)(size_t)(texID);

    glBindTexture(GL_TEXTURE_2D, gltex);
    
    glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, VIEW_WIDTH, VIEW_HEIGHT,
                    GL_RGBA, GL_UNSIGNED_BYTE, pFrameRGB->data[0]);

    glGetError();
    return;
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API GetRenderEventFunc()
{
    return OnRenderEvent;
}

