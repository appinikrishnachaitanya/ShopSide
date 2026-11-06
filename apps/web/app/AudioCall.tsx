"use client";
import { useEffect, useRef, useState } from "react";
export default function AudioCall({
  roomId,
  online,
}: {
  roomId: string;
  online: boolean;
}) {
  const [status, setStatus] = useState("idle"),
    [muted, setMuted] = useState(false),
    [error, setError] = useState("");
  const ws = useRef<WebSocket | null>(null),
    pc = useRef<RTCPeerConnection | null>(null),
    stream = useRef<MediaStream | null>(null),
    audio = useRef<HTMLAudioElement | null>(null),
    pending = useRef<RTCIceCandidateInit[]>([]),
    initiator = useRef(false),
    timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stop = () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    ws.current?.close();
    ws.current = null;
    pc.current?.close();
    pc.current = null;
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    pending.current = [];
    initiator.current = false;
    setMuted(false);
    setStatus("idle");
  };
  useEffect(
    () => () => {
      ws.current?.close();
      pc.current?.close();
      stream.current?.getTracks().forEach((t) => t.stop());
    },
    [roomId],
  );
  async function join() {
    try {
      setError("");
      setStatus("joining");
      const media = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: false,
      });
      stream.current = media;
      const cfg = await fetch("/api/rooms/" + roomId + "/call-config");
      if (!cfg.ok) throw new Error("Voice configuration unavailable");
      const peer = new RTCPeerConnection(await cfg.json());
      pc.current = peer;
      media.getTracks().forEach((t) => peer.addTrack(t, media));
      const socket = new WebSocket(
        (location.protocol === "https:" ? "wss://" : "ws://") +
          location.host +
          "/api/rooms/" +
          roomId +
          "/call",
      );
      ws.current = socket;
      const send = (type: string, payload?: unknown) => {
        if (socket.readyState === WebSocket.OPEN)
          socket.send(JSON.stringify({ type, payload }));
      };
      peer.onicecandidate = (e) => {
        if (e.candidate) send("ice", e.candidate.toJSON());
      };
      peer.ontrack = (e) => {
        if (audio.current) {
          audio.current.srcObject = e.streams[0];
          audio.current
            .play()
            .catch(() => setError("Tap the audio player to hear your friend."));
        }
      };
      peer.onconnectionstatechange = () => {
        if (peer.connectionState === "connected") {
          if (timer.current) clearTimeout(timer.current);
          setStatus("connected");
        }
        if (["failed", "disconnected"].includes(peer.connectionState))
          setError("Call connection interrupted. Hang up and try again.");
      };
      socket.onopen = () => setStatus("waiting");
      socket.onerror = () =>
        setError("Call signaling failed. Check your connection.");
      socket.onclose = () => {
        if (ws.current === socket) {
          setError("Call disconnected.");
          stop();
        }
      };
      socket.onmessage = async (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === "peer_ready" && !initiator.current) {
            setStatus("connecting");
            timer.current = setTimeout(
              () =>
                setError(
                  "Could not establish audio. Check network access or configure a TURN relay.",
                ),
              20000,
            );
            initiator.current = true;
            const offer = await peer.createOffer();
            await peer.setLocalDescription(offer);
            send("offer", offer);
          } else if (data.type === "offer") {
            setStatus("connecting");
            timer.current = setTimeout(
              () =>
                setError(
                  "Could not establish audio. Check network access or configure a TURN relay.",
                ),
              20000,
            );
            await peer.setRemoteDescription(data.payload);
            for (const c of pending.current) await peer.addIceCandidate(c);
            pending.current = [];
            const answer = await peer.createAnswer();
            await peer.setLocalDescription(answer);
            send("answer", answer);
          } else if (data.type === "answer") {
            await peer.setRemoteDescription(data.payload);
            for (const c of pending.current) await peer.addIceCandidate(c);
            pending.current = [];
          } else if (data.type === "ice") {
            if (peer.remoteDescription)
              await peer.addIceCandidate(data.payload);
            else pending.current.push(data.payload);
          } else if (data.type === "hangup") {
            setError("Your friend left the call.");
            stop();
          }
        } catch {
          setError("Could not connect the call. Please try again.");
        }
      };
    } catch {
      setError("Microphone permission is needed to join a call.");
      stop();
    }
  }
  return (
    <section className="call-panel" aria-label="Voice call">
      <div>
        <span className="call-icon" aria-hidden="true">
          ◌
        </span>
        <div>
          <strong>Talk while you shop</strong>
          <small>
            {status === "idle"
              ? "Audio is off"
              : status === "waiting"
                ? "Waiting for your friend to join…"
                : status === "joining" || status === "connecting"
                  ? "Connecting…"
                  : "Voice connected"}
          </small>
        </div>
      </div>
      <audio
        ref={audio}
        autoPlay
        controls
        hidden={status === "idle"}
        className="call-audio"
        aria-label="Friend audio"
      />
      {status === "idle" ? (
        <button disabled={!online} onClick={join}>
          Join voice
        </button>
      ) : (
        <div className="call-actions">
          <button
            onClick={() => {
              stream.current
                ?.getAudioTracks()
                .forEach((t) => (t.enabled = muted));
              setMuted(!muted);
            }}
          >
            {muted ? "Unmute" : "Mute"}
          </button>
          <button onClick={stop}>Leave</button>
        </div>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
