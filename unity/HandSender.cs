using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

public class HandSender : MonoBehaviour
{
    [Header("서버 설정")]
    public string serverIP   = "192.168.x.x";  // Inspector에서 Linux PC IP로 변경
    public int    serverPort = 5159;

    [Header("손 위치 기준 오브젝트")]
    public Transform rightHandAnchor;

    private UdpClient  _udp;
    private IPEndPoint _endpoint;
    private float      _timer = 0f;
    private const float INTERVAL = 1f / 20f;  // 20Hz

    private void Start()
    {
        _udp      = new UdpClient();
        _endpoint = new IPEndPoint(IPAddress.Parse(serverIP), serverPort);
        Debug.Log($"UDP 전송 준비: {serverIP}:{serverPort}");
    }

    private void Update()
    {
        _timer += Time.deltaTime;
        if (_timer < INTERVAL) return;
        _timer = 0f;
        SendPose();
    }

    private void SendPose()
    {
        if (rightHandAnchor == null) return;

        Vector3    pos = rightHandAnchor.position;
        Quaternion rot = rightHandAnchor.rotation;

        string json = "{\"type\":\"hand_pose\"," +
                      "\"position\":{\"x\":" + pos.x.ToString("F4") +
                      ",\"y\":" + pos.y.ToString("F4") +
                      ",\"z\":" + pos.z.ToString("F4") + "}," +
                      "\"rotation\":{\"x\":" + rot.x.ToString("F4") +
                      ",\"y\":" + rot.y.ToString("F4") +
                      ",\"z\":" + rot.z.ToString("F4") +
                      ",\"w\":" + rot.w.ToString("F4") + "}}";

        byte[] data = Encoding.UTF8.GetBytes(json);
        _udp.Send(data, data.Length, _endpoint);
    }

    private void OnDestroy()
    {
        _udp?.Close();
    }
}
