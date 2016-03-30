using System;
using UnityEngine;
using System.Collections;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.IO;
using System.Threading;
using System.Text;


namespace VES
{
	public class VideoPlane : MonoBehaviour
	{
		/* This func is used to test dll import status. */
		#if UNITY_IPHONE && !UNITY_EDITOR
		[DllImport ("__Internal")]
		#else
		[DllImport ("libdavid")]
		#endif
		private static extern int dlltest ();


		#if UNITY_IPHONE && !UNITY_EDITOR
		[DllImport ("__Internal")]
		#else
		[DllImport ("libdavid")]
		#endif
		private static extern int init (string addr, int texture);


		#if UNITY_IPHONE && !UNITY_EDITOR
		[DllImport ("__Internal")]
		#else
		[DllImport ("libdavid")]
		#endif
		private static extern IntPtr GetRenderEventFunc();


		#if UNITY_IPHONE && !UNITY_EDITOR
		[DllImport ("__Internal")]
		#else
		[DllImport ("libdavid")]
		#endif
		private static extern int terminate();

		private Thread render_thread;
		private string addr;
		private Texture2D texture;
		private int texID;
		private int width=1024;
		private int height=512;
		public bool forward;


		void Start ()
		{
			texture = new Texture2D (width, height, TextureFormat.RGB24, false);
			texture.filterMode = FilterMode.Point;
			texture.Apply ();
			GetComponent<Renderer> ().material.mainTexture = texture;
			#if UNITY_EDITOR
			if(forward)
			{
				addr = "udp://192.168.1.100:6665";
				Debug.Log("EDITOR-转发视频接收模式: "+addr);
			}
			else
			{
				addr = "udp://127.0.0.1:6666";
				Debug.Log("EDITOR-直发视频接收模式: "+addr);
			}
			#else
			addr = "udp://0.0.0.0:6666";
			Debug.Log("iPhone-全局接收模式: "+addr);
			#endif
			texID = texture.GetNativeTexturePtr ().ToInt32();
			render_thread = new Thread (new ThreadStart (decode_stream));
			render_thread.Start ();

			//Debug.Log ("start");
		}

		private void stopThread ()
		{
			if (render_thread.IsAlive) {
				terminate ();
				render_thread.Abort ();
			}
		}

		private void decode_stream ()
		{
			init(addr,texID);
		}

		void OnApplicationQuit ()
		{
			stopThread ();
		}
			
		void Update ()
		{
			GL.IssuePluginEvent(GetRenderEventFunc(), texID);
		}
	}
}