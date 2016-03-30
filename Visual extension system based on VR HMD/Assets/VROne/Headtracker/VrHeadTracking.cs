using UnityEngine;
using System.Collections;

namespace VROne
{
	public class VrHeadTracking : MonoBehaviour {

		public bool resetViewOnTouch = false;
		public static VrHeadTracking instance;
		public enum QuaternionFilterMethod
		{
			WeightFilter,
			ThresholdFilter,
			HybridFilter,
			MaybeBetterFilter,
		};
		// Use this for initialization
		void Start () {
			instance = this;

			//Set the initial rotation to align the virtual world with the real world on start
			initialRotation = Quaternion.Euler (new Vector3 (0, 0, 0));


#if UNITY_IPHONE
			HeadTrackingIOS.StartCameraUpdates();
#endif
#if UNITY_ANDROID
			HeadTrackingAndroid.Initialize();
#endif
			#if TRACKING_SPEED
			StartCoroutine (UpdateTrackingSpeed ());
			#endif
		}
		#if TRACKING_SPEED
		int tracking_count;

		IEnumerator UpdateTrackingSpeed()
		{
			while (true)
			{
				float timeElapsed = 0;
				tracking_count = 0;
				while (timeElapsed < 1.0f)
				{
					timeElapsed += Time.deltaTime;
					yield return null;
				}
				Debug.Log("TrackingSpeed: "+tracking_count);
			}
		}
		#endif
		Quaternion initialRotation = Quaternion.identity;
		Quaternion new_rotation = Quaternion.identity;
		public void ResetView()
		{
			recenter = true;
		}



		bool recenter = false;


		public float Included_Angle(float a,float b)
		{
			float dmin, dmax;
			dmin = a > b ? b : a;
			dmax = a > b ? a : b;
			if ((dmax - dmin) > 180.0f) 
			{
				return dmin + 360.0f - dmax;
			} else 
			{
				return dmax - dmin;
			}
		}



		private Quaternion Threshold(Quaternion old_q,Quaternion new_q,float lower_bound=0.1f)
		{
			if ((
				Included_Angle (old_q.eulerAngles [0],new_q.eulerAngles [0]) > lower_bound ||
				Included_Angle (old_q.eulerAngles [1],new_q.eulerAngles [1]) > lower_bound ||
				Included_Angle (old_q.eulerAngles [2],new_q.eulerAngles [2]) > lower_bound )
			) 
			{
				return new_q;
			}
			return old_q;
		}

		private Quaternion Weight(Quaternion old_q,Quaternion new_q)
		{
			Vector3 ans_v = Vector3.zero;
			Vector3 old_v = old_q.eulerAngles;
			Vector3 new_v = new_q.eulerAngles;
			float t1, t2;
			for (int i = 0; i < 3; i++) {
				
				t1 = old_v [i] > new_v [i] ? new_v [i] : old_v [i];
				t2 = old_v [i] > new_v [i] ? old_v [i] : new_v [i];
				if ((t2 - t1) > 180.0f) 
				{
					ans_v [i] = (old_v [i] * 0.65f + new_v [i] * 0.35f + 360.0f * (t1 == old_v [i] ? 0.65f : 0.35f)) % 360.0f;
				} else 
				{
					ans_v [i] = old_v [i] * 0.65f + new_v [i] * 0.35f;
				}
			}
			return Quaternion.Euler (ans_v);
//			return Quaternion.Euler (0.65f * old_q.eulerAngles + 0.35f * new_q.eulerAngles);
		}

		private Quaternion Hybrid(Quaternion old_q,Quaternion new_q)
		{
			return Weight(old_q,Threshold(old_q,new_q));
		}

		public Quaternion QuaternionFilter(Quaternion old_q,Quaternion new_q,QuaternionFilterMethod method)
		{
			//Debug.Log ("X:" + new_q.eulerAngles [0] + " Y: " + new_q.eulerAngles [1] + " Z: " + new_q.eulerAngles [2]);
			Quaternion ans_q = Quaternion.identity;
			switch (method) 
			{
			case QuaternionFilterMethod.WeightFilter:
				ans_q = Weight (old_q, new_q);
				break;
			case QuaternionFilterMethod.ThresholdFilter:
				ans_q = Threshold (old_q, new_q);
				break;
			case QuaternionFilterMethod.HybridFilter:
				ans_q = Hybrid (old_q, new_q);
				break;
			case QuaternionFilterMethod.MaybeBetterFilter:
				ans_q = new_q;
				break;
			default:
				ans_q = new_q;
				break;
			}
			return ans_q;
		}

		// Update is called once per frame
		void Update() {
	#if UNITY_IPHONE && !UNITY_EDITOR
			Quaternion rot = HeadTrackingIOS.GetQuaternionUpdate();
			if (recenter || resetViewOnTouch && (Input.touchCount > 0))
			{
				initialRotation = rot;
				recenter = false;
			}

			new_rotation = Quaternion.Inverse(initialRotation) * rot; //works for landscape left
			transform.rotation = QuaternionFilter(transform.rotation,new_rotation,QuaternionFilterMethod.HybridFilter);

	#endif
	#if UNITY_ANDROID && !UNITY_EDITOR
			Quaternion rot = HeadTrackingAndroid.GetQuaternionUpdate();
			transform.rotation = Quaternion.Inverse(initialRotation) * rot; //works for landscape left
			if (recenter || resetViewOnTouch && (Input.touchCount > 0))
			{
				initialRotation = rot;
				recenter = false;
			}
	#endif
			//Debug.Log ("A: "+transform.eulerAngles[0]+" B: "+transform.eulerAngles[1]+" C: "+transform.eulerAngles[2]);
			#if TRACKING_SPEED
			tracking_count++;
			#endif
		}
	}
}