//
//  libdavid.h
//  libdavid-ios
//
//  Created by 杜佑宸 on 16/3/2.
//  Copyright © 2016年 杜佑宸. All rights reserved.
//

#ifndef libdavid_h
#define libdavid_h
extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavformat/avio.h>
#include <libswresample/swresample.h>
#include <libswscale/swscale.h>
#include <libavutil/opt.h>
}
#include "IUnityGraphics.h"

#include <OpenGLES/ES2/gl.h>


#include <cstdio>
#include <cassert>
#include <cmath>
#include <cstdlib>
#include <unistd.h>
#include <pthread.h>

using namespace std;


#define VIEW_WIDTH 1024
#define VIEW_HEIGHT 512

#define FF_QUIT_EVENT 1

typedef struct PacketQueue
{
    AVPacketList *first_pkt, *last_pkt;
    int nb_packets;
    int size;
    pthread_mutex_t mutex;
    pthread_cond_t cond;
} PacketQueue;



typedef struct VideoState
{
    AVFormatContext *pFormatCtx;
    int             videoStream;
    
    AVStream        *video_st;
    PacketQueue     videoq;
    
    pthread_t       video_tid;
    pthread_t       parse_tid;
    
    char            filename[1024];
    int             quit;
    
    AVIOContext     *io_context;
    struct SwsContext *sws_ctx;
    
    int             textureId;
} VideoState;


void packet_queue_init(PacketQueue *q);
int packet_queue_put(PacketQueue *q, AVPacket *pkt);
static int packet_queue_get(PacketQueue *q, AVPacket *pkt, int block);
int init_picture(VideoState *is, AVFrame *pFrame);
void *video_thread(void *arg);
int stream_component_open(VideoState *is, int stream_index);
int decode_interrupt_cb(void *opaque);
void *decode_thread(void *arg);
extern "C" int UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API init(char* name, int textureId);
extern "C" int UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API dlltest();
static void UNITY_INTERFACE_API OnRenderEvent(int texID);
extern "C" UnityRenderingEvent UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API GetRenderEventFunc();
extern "C" void UNITY_INTERFACE_EXPORT UNITY_INTERFACE_API RenderFrame(int texID);





#endif /* libdavid_h */
