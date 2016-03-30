using System;

using UnityEngine;
using System.Collections;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;

namespace VES
{
	public class VideoRender:MonoBehaviour
	{
		private const int VIDEO_WIDTH=300;
		private const int VIDEO_HEIGHT=300;
		private Texture2D texture;
		private UdpClient client;
		private IPEndPoint receive_point;
		private Thread udp_thread;
		void Start()
		{
			client = new UdpClient (new IPEndPoint(IPAddress.Any, 8091));
			texture = new Texture2D (VIDEO_WIDTH, VIDEO_HEIGHT,TextureFormat.ARGB32,false);
			GetComponent<Renderer>().material.mainTexture = texture; 
			receive_point = new IPEndPoint (IPAddress.Any, 0);
//			client.Client.Blocking = false;
			udp_thread = new Thread (new ThreadStart (Update_Texture));
//			Debug.Log ("thread about to start");
			udp_thread.Start ();
//			Debug.Log ("thread start");
		}
		private void Update_Texture()
		{
			// Get data through udp
			// analyze data
			// set texture
			while (true) {
				//Debug.Log ("Waiting data...");
				try{
				Byte[] receiveBytes = client.Receive (ref receive_point); 
				string returnData = ASCIIEncoding.ASCII.GetString (receiveBytes);
				Debug.Log (returnData.ToString ());
				}
				catch(Exception err) {
					Debug.Log (err.Message);
				}
			}

		}
		private void Set_Texture()
		{
//			i = (i + 1) % 20;
//			//Debug.Log (webcam.GetPixel (1, 1));
//			for (int y = 0; y < texture.height; y++) {
//				for (int x = 0; x < texture.width; x++) {
//					Color color = ((x+i) % 20 > 10 || (y+i) % 20 > 10 ? Color.white : Color.black);
//					texture.SetPixel(x, y, color);
//				}
//			}
//			texture.Apply();
		}
		void Update()
		{
		}
		private void stopThread()
		{
			if (udp_thread.IsAlive)
			{
				udp_thread.Abort();
			}
			client.Close();
		}
		void OnApplicationQuit()
		{
			stopThread();
		}
	}
}

