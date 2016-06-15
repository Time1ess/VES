#Vision Extension System Based on VR HMD
#####2016.6.15
---
##开发相关
###显示终端
    1. 使用VR One SDK，采用Unity 5.3.4f1构建Xcode项目，使用Xcode 7.3编译生成iOS程序。
    2. Unity Scripts中使用了基于FFmpeg和OpenGL ES3编写的视频流解析插件完成视频流解析。
###视频终端
    1. 使用Python开发，各模块采用类封装，初始化后除vffmpeg类以外自包含工作线程，无需单独创建工作线程。
    2. FFmpeg视频流创建使用了shell命令，通过Python的os.system模块调用，需要单独创建进程。
    3. system.py 文件作为整个系统的入口，负责调用所有模块并初始化。
###中间件服务器
    1. 使用Python开发，各模块采用类封装，同视频终端。
    2. Visualization实例将会通过Python multiprocessing中的Queue从Connection实例获取指定格式的数据并进行可视化线程。
    3. Connection实例将会广播信息非阻塞等待连接，在确认连接完成后循环等待数据输入并进行下一步处理。
##额外事项
    1. 在当前开发进度下，视频终端采用Raspberry Pi 2 Model B作为控制器，使用Raspbian作为操作系统，通过GPIO扩展板扩展GPIO口，两个步进电机通过L293D电机控制芯片接入GPIO扩展板，MPU6050芯片通过I2C总线接入GPIO扩展板，树莓派通过搭载的原生摄像头模块完成视频采集工作。
    2. 中间件服务器与硬件无关，只要支持Python语言且运算能力理论上高于视频采集终端的机器都可以作为中间件服务器。
    3. 显示终端在当前开发进度下使用了iPhone6作为显示设备，结合VR One完成设计。
    4. 由于先启动中间件服务器数据会溢出，因此推荐启动顺序为：显示、视频终端->中间件服务器
    
    