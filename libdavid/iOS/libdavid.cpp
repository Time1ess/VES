#include "libdavid.h"

VideoState *gs;
AVFrame *pFrameRGB[FRAME_SIZE];
bool pFrameRGB_status[FRAME_SIZE];

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


int get_frame_status(VideoState *is,FRAME_STATUS type)
{
//    return 0;
    int index=FRAME_SIZE;
    if(is==NULL)
        return index;
    if(is->frames_status[0]==type)
        return 0;
    return index;
}

void set_frame_status(VideoState *is,FRAME_STATUS type)
{
    is->frames_status[0]=type;
}

int init_picture(VideoState *is, int index)
{
    if(is->quit||index<0||index>=FRAME_SIZE)
        return -1;
    sws_scale(
              is->sws_ctx[index],
              (uint8_t const * const *)is->frames[index]->data,
              is->frames[index]->linesize,
              0,
              is->video_st->codec->height,
              pFrameRGB[index]->data,
              pFrameRGB[index]->linesize
              );
    return 0;
}

void *transcode_thread(void *arg)
{
    
    //fprintf(stdout, "[FFmpeg-video thread] transcode thread [%d] created\n",thread_count++);
    VideoState *is = (VideoState *)arg;
    int index;
    for(;;)
    {
        if(is->quit)
        {
            break;
        }
        pthread_mutex_lock(&is->mutex);
        pthread_cond_wait(&is->cond, &is->mutex);
        index=get_frame_status(is, FRAME_WAIT_TRANSCODE);
        pthread_mutex_unlock(&is->mutex);
        if(index!=FRAME_SIZE)
        {
            init_picture(is, index);
            set_frame_status(is, FRAME_WAIT_READ);
        }
    }
    fprintf(stdout, "[FFmpeg-transcode thread] thread terminated\n");
    return NULL;
}


void *video_thread(void *arg)
{
    //fprintf(stdout, "[FFmpeg-decode thread] video_thread created\n");
    VideoState *is = (VideoState *)arg;
    AVPacket pkt1, *packet = &pkt1;
    int frameFinished=0;
    int index=0;

    pthread_create(&is->trans_tid, NULL, transcode_thread, (void *)is);
    
    //fprintf(stdout, "[FFmpeg-video thread] decode frame\n");
    index=get_frame_status(is,FRAME_WAIT_WRITE);
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
        
        avcodec_decode_video2(is->video_st->codec, is->frames[index], &frameFinished, packet);
        
        if(frameFinished)
        {
            if(index!=FRAME_SIZE)
            {
                pthread_mutex_lock(&is->mutex);
                pthread_cond_signal(&is->cond);
                set_frame_status(is, FRAME_WAIT_TRANSCODE);
                pthread_mutex_unlock(&is->mutex);
            }
            index=get_frame_status(is,FRAME_WAIT_WRITE);
        }
        av_free_packet(packet);
    }
    
    fprintf(stdout, "[FFmpeg-video thread] thread terminated\n");
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
        for(int i=0;i<FRAME_SIZE;i++)
        {
            is->sws_ctx[i] = sws_getContext
            (
             is->video_st->codec->width,
             is->video_st->codec->height,
             is->video_st->codec->pix_fmt,
             VIEW_WIDTH,
             VIEW_HEIGHT,
             AV_PIX_FMT_RGB24,
             SWS_FAST_BILINEAR,
             NULL,
             NULL,
             NULL
             );
        }
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
    //fprintf(stdout, "[FFmpeg-main thread] decode_thread created\n");
    VideoState *is = (VideoState *)arg;
    AVFormatContext *pFormatCtx = NULL;
    AVPacket pkt1, *packet = &pkt1;
    
    AVIOInterruptCB callback;
    
    int video_index = -1;
    int i;
    
    is->videoStream=-1;
    
    // Will interrupt blocking functions ifwe quit!
    callback.callback = decode_interrupt_cb;
    callback.opaque = is;
    
    fprintf(stdout, "[FFmpeg-decode thread] Try to open I/O\n");
    if(avio_open2(&is->io_context, is->filename, 0, &callback, NULL) < 0)
    {
        fprintf(stdout, "Unable to open I/O for file\n");
        return NULL;
    }
    //fprintf(stdout, "avio_open2 done\n");
    
    // Open video file
    fprintf(stdout, "[FFmpeg-decode thread] Try to open format context\n");
    if(avformat_open_input(&pFormatCtx, is->filename, NULL, NULL)!=0)
    {
        fprintf(stdout, "Couldn't Open file\n");
        return NULL; // Couldn't open file
    }
    //fprintf(stdout, "open_input done\n");
    
    is->pFormatCtx = pFormatCtx;
    
    // Retrieve stream information
    fprintf(stdout, "[FFmpeg-decode thread] Try to Retrieve stream info\n");
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
    //fprintf(stdout, "[FFmpeg-decode thread] read frame\n");
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
        {
            packet_queue_put(&is->videoq, packet);
            //fprintf(stdout, "packs ready to load: %d\n",is->videoq.nb_packets);
        }
        else
            av_free_packet(packet);
    }
    fprintf(stdout, "[FFmpeg-decode thread] thread terminated\n");
    return NULL;
}

extern "C" int UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API init(char* name, int textureId)
{
    // Register all formats and codecs
    if(name == NULL) return -1;
    av_register_all();
    avformat_network_init();
    
    uint8_t *buffers[FRAME_SIZE];
    
    int buffer_size;
    buffer_size = avpicture_get_size(AV_PIX_FMT_RGB24, VIEW_WIDTH, VIEW_HEIGHT);
    
    for(int i=0;i<FRAME_SIZE;i++)
    {
        buffers[i] = (uint8_t *) av_malloc(buffer_size*sizeof(uint8_t));
        pFrameRGB[i]=av_frame_alloc();
        avpicture_fill((AVPicture *) pFrameRGB[i], buffers[i], AV_PIX_FMT_RGB24,
                       VIEW_WIDTH, VIEW_HEIGHT);
    }
    
    VideoState *is;
    is = (VideoState*)av_mallocz(sizeof(VideoState));
    gs = is;
    
    strcpy(is->filename, name);
    is->textureId = textureId;
    for(int i=0;i<FRAME_SIZE;i++)
    {
        is->frames[i]=av_frame_alloc();
        pFrameRGB_status[i]=false;
    }
    is->frames[FRAME_SIZE]=av_frame_alloc();
    is->mutex=PTHREAD_MUTEX_INITIALIZER;
    is->cond=PTHREAD_COND_INITIALIZER;

    pthread_create(&is->parse_tid, NULL, decode_thread, is);
    
    if(!is->parse_tid)
    {
        av_free(is);
        return -1;
    }
    int ret = 0;
    // OpenGL ES init.
    glEnable(GL_TEXTURE_2D);
    glEnable(GL_BLEND);
    glBlendFunc(GL_ONE, GL_SRC_COLOR);
    
    // End init.
    fprintf(stdout, "[FFmpeg-main thread] wait for event\n");
    
    for(;;)
    {
        pthread_mutex_lock(&event_mutex);
        pthread_cond_wait(&event_cond, &event_mutex);
        switch(event_type)
        {
            case FF_QUIT_EVENT:
                ret = pthread_join(is->parse_tid, NULL);
                if(ret)
                    fprintf(stdout, "decode_thread exit with error.\n");
                else
                    fprintf(stdout, "decode_thread exit with no error.\n");
                ret = pthread_join(is->video_tid, NULL);
                if(ret)
                    fprintf(stdout, "video_thread exit error.\n");
                else
                    fprintf(stdout, "video_thread exit with no error.\n");
                ret = pthread_join(is->trans_tid, NULL);
                if(ret)
                    fprintf(stdout, "transcode thread exit error.\n");
                else
                    fprintf(stdout, "transcode_thread exit with no error.\n");
                av_frame_free(&pFrameRGB[0]);
                av_frame_free(&pFrameRGB[1]);
                fprintf(stdout, "[FFmpeg-main thread] thread terminated\n");
                return 0;
                break;
            default:
                break;
        }
        pthread_mutex_unlock(&event_mutex);
    }
    return 0;
}

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
    int index;
    glBindTexture(GL_TEXTURE_2D, gltex);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR);
    index=get_frame_status(gs, FRAME_WAIT_READ);
    if(index!=FRAME_SIZE&&pFrameRGB[index])
    {
        glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, VIEW_WIDTH, VIEW_HEIGHT,
                        GL_RGB, GL_UNSIGNED_BYTE, pFrameRGB[index]->data[0]);
        set_frame_status(gs, FRAME_WAIT_WRITE);
    }
    glBindTexture(GL_TEXTURE_2D, 0);
}

extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API GetRenderEventFunc()
{
    return OnRenderEvent;
}

