import { useEnvironmentStore } from '../../stores/environment';

const CITIES = [
  { name: 'Ghent', lat: 51.0447, lon: 3.7268 },
  { name: 'New York', lat: 40.7128, lon: -74.006 },
  { name: 'Paris', lat: 48.8566, lon: 2.3522 },
  { name: 'Tokyo', lat: 35.6762, lon: 139.6503 },
];

export function EnvironmentEmptyState() {
  const source = useEnvironmentStore((s) => s.source);
  const setSource = useEnvironmentStore((s) => s.setSource);
  const setLocation = useEnvironmentStore((s) => s.setLocation);
  const setLocationFormatted = useEnvironmentStore((s) => s.setLocationFormatted);
  const setLocationQuery = useEnvironmentStore((s) => s.setLocationQuery);

  if (source !== 'none') return null;

  const handleCity = (city: (typeof CITIES)[number]) => {
    setSource('osm');
    setLocation(city.lat, city.lon);  // TWO POSITIONAL ARGS
    setLocationFormatted(city.name);
    setLocationQuery(city.name);
    useEnvironmentStore.getState().fetchOSM();
  };

  return (
    <div className="text-xs text-zinc-500 py-2">
      <p>Load real-world buildings from OpenStreetMap</p>
      <div className="flex flex-wrap gap-1.5 mt-2">
        {CITIES.map((city) => (
          <button
            key={city.name}
            onClick={() => handleCity(city)}
            className="px-2 py-1 rounded bg-zinc-800 border border-zinc-700
              hover:border-zinc-500 text-zinc-400 hover:text-zinc-200
              transition-colors"
          >
            {city.name}
          </button>
        ))}
      </div>
    </div>
  );
}
