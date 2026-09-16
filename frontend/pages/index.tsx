import { useEffect, useState } from 'react';

interface TickEvent {
  tick: number;
  type: string;
  data: Record<string, unknown>;
}

interface AgentState {
  id: string;
  hunger: number;
  health: number;
  energy: number;
  social: number;
}

export default function Observer() {
  const [events, setEvents] = useState<TickEvent[]>([]);
  const [agents, setAgents] = useState<AgentState[]>([]);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    fetch('/simulation-snapshot.json')
      .then(r => r.json())
      .then(data => {
        setEvents(data.events || []);
        setAgents(data.agents || []);
        setTick(data.tick || 0);
      });
  }, []);

  return (
    <div style={{ padding: '1rem', fontFamily: 'system-ui' }}>
      <h1>Eidolon Observer</h1>
      <p>Simulation tick: {tick}</p>
      <p>Agents: {agents.length}</p>
      <h2>Agent States</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th><th>Hunger</th><th>Health</th><th>Energy</th><th>Social</th>
          </tr>
        </thead>
        <tbody>
          {agents.map(a => (
            <tr key={a.id}>
              <td>{a.id}</td>
              <td>{a.hunger.toFixed(3)}</td>
              <td>{a.health.toFixed(3)}</td>
              <td>{a.energy.toFixed(3)}</td>
              <td>{a.social.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h2>Recent Events</h2>
      <ul>
        {events.slice(-20).map((e, i) => (
          <li key={i}>{e.type} ({e.data?.action || ''})</li>
        ))}
      </ul>
    </div>
  );
}
