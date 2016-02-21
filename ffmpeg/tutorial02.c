// A pedagogical video player that will stream through every video frame as fast as it can.
// //
// // Use
// // 
// // gcc `pkg-config --cflags -libs libavutil libavformat libavcodec
//          libswscale` `sdl-config --cflags --libs`-o tutorial02 
//          tutorial02.c 
// // to build (assuming libavformat and libavcodec are correctly installed, 
// // and assuming you have sdl-config. Please refer to SDL docs for your installation.)
// //
// // Run using
// // tutorial02 myvideofile.mpg
// //
// // to play the video stream on your screen.
//

#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libswscale/swscale.h>
#include <SDL.h>
#include <SDL_thread.h>
#include <stdio.h>


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

    // Find the first video stream
    int videoStream = -1;
    for(i=0; i < pFormatCtx->nb_streams; i++)
        if(pFormatCtx->streams[i]->codec->codec_type == AVMEDIA_TYPE_VIDEO)
        {
            videoStream = i;
            break;
        }
    if(videoStream == -1)
    {
        fprintf(stderr, "Didn't find a video stream!\n");
        return -1;  // Didn't find a video stream
    }

    // Get a pointer to the codec context for the video stream
    pCodecCtxOrig = pFormatCtx->streams[videoStream]->codec;

    AVCodec *pCodec = NULL;

    // Find the decoder for the video stream
    pCodec = avcodec_find_decoder(pCodecCtxOrig->codec_id);
    if(pCodec == NULL)
    {
        fprintf(stderr, "Unsupported codec!\n");
        return -1;
    }
    // Copy context
    pCodecCtx = avcodec_alloc_context3(pCodec);

    if(avcodec_copy_context(pCodecCtx, pCodecCtxOrig) != 0)
    {
        fprintf(stderr, "Couldn't copy codec context");
        return -1;  // Error copying codec context
    }
    // Open codec
    if(avcodec_open2(pCodecCtx, pCodec, NULL) < 0)
    {
        fprintf(stderr, "Couldn't open codec!\n");
        return -1;  // Could not open codec
    }

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

        SDL_Event event;

        // Free the packet that was allocated by av_read_frame
        av_free_packet(&packet);
        SDL_PollEvent(&event);
        switch(event.type)
        {
            case SDL_QUIT:
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
