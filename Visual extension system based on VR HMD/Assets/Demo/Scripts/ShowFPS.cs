using UnityEngine;
using System.Collections;

public class ShowFPS : MonoBehaviour {

	void Start()
	{
		//Debug.Log ("Show Fps!");
		StartCoroutine (UpdateFPS ());
	}



	void OnGUI()
	{
		GUI.Label (new Rect (0, 0, 150, 20), "每秒渲染帧数: " + fps2+" fps");
	}
		
	int fps2;

	IEnumerator UpdateFPS()
	{
		while (true)
		{
			float timeElapsed = 0;
			int frameCount = 0;
			while (timeElapsed < 1.0f)
			{
				frameCount++;
				timeElapsed += Time.deltaTime;
				yield return null;
			}
			fps2 = frameCount;
			//Debug.Log(fps + ", " +fps2);
		}
	}
}
