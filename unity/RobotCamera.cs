using System.Collections;
using UnityEngine;
using UnityEngine.Networking;
using UnityEngine.UI;

public class RobotCamera : MonoBehaviour
{
    [Header("카메라 서버")]
    public string snapshotUrl = "http://192.168.x.x:8080/snapshot";  // Inspector에서 PC IP로 변경
    [Range(5, 30)]
    public int fpsTarget = 20;

    [Header("표시 대상")]
    public RawImage displayUI;
    public Renderer displayMesh;

    private Texture2D _tex;
    private bool _running = true;

    private void Start()
    {
        Debug.Log($"[Camera] 시작: {snapshotUrl}");
        if (displayMesh == null) displayMesh = GetComponent<Renderer>();

        // 셰이더 찾기 (URP 우선, 없으면 fallback)
        Shader sh = Shader.Find("Universal Render Pipeline/Unlit");
        if (sh == null) sh = Shader.Find("Unlit/Texture");
        if (sh == null) sh = Shader.Find("Sprites/Default");

        if (sh != null)
        {
            displayMesh.material = new Material(sh);
            Debug.Log($"[Camera] 셰이더 적용: {sh.name}");
        }
        else
        {
            Debug.LogError("[Camera] 셰이더를 찾을 수 없음! 기존 머티리얼 유지");
        }

        _tex = new Texture2D(2, 2);
        if (displayUI   != null) displayUI.texture              = _tex;
        if (displayMesh != null) displayMesh.material.mainTexture = _tex;
        StartCoroutine(StreamLoop());
    }

    private void OnDestroy()
    {
        _running = false;
        Destroy(_tex);
    }

    private IEnumerator StreamLoop()
    {
        float interval = 1f / fpsTarget;
        while (_running)
        {
            using (var req = UnityWebRequest.Get(snapshotUrl))
            {
                req.timeout = 2;
                yield return req.SendWebRequest();

                if (req.result == UnityWebRequest.Result.Success)
                {
                    _tex.LoadImage(req.downloadHandler.data);
                    if (displayMesh != null)
                        displayMesh.material.mainTexture = _tex;
                }
                else
                {
                    Debug.LogWarning($"카메라 수신 실패: {req.error}");
                }
            }
            yield return new WaitForSeconds(interval);
        }
    }
}
