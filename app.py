import React, { useState, useMemo } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  AreaChart, Area, PieChart, Pie, Cell 
} from 'recharts';
import { 
  TrendingUp, TrendingDown, Wallet, Home, PiggyBank, 
  AlertTriangle, CheckCircle, Info, PlusCircle, Users,
  Calendar, ArrowUpRight, ArrowDownRight
} from 'lucide-react';

const App = () => {
  // Estats de dades basats en la vostra situació familiar real
  const [data, setData] = useState({
    ingressos: [
      { nom: 'Lloguer Pis', import: 850, categoria: 'Lloguer', icona: <Home size={16} /> },
      { nom: 'Aportació Alba', import: 1200, categoria: 'Familiar', icona: <Users size={16} /> },
      { nom: 'Subsidi Atur', import: 480, categoria: 'Atur', icona: <Wallet size={16} /> },
    ],
    despeses: [
      { nom: 'Hipoteca BBVA', import: 376, categoria: 'Habitatge' },
      { nom: 'Préstec Personal', import: 165, categoria: 'Deutes' },
      { nom: 'Comunitat', import: 60, categoria: 'Habitatge' },
      { nom: 'IBI (Prorratejat)', import: 35, categoria: 'Impostos' },
      { nom: 'Alimentació', import: 450, categoria: 'Vida' },
      { nom: 'Subministraments', import: 140, categoria: 'Vida' },
      { nom: 'Oci/Varies', import: 200, categoria: 'Vida' },
    ],
    historics: [
      { mes: 'Set', estalvi: 200 },
      { mes: 'Oct', estalvi: 150 },
      { mes: 'Nov', estalvi: 300 },
      { mes: 'Des', estalvi: -50 },
      { mes: 'Gen', estalvi: 420 },
      { mes: 'Feb', estalvi: 744 }, // Balanç actual estimat
    ]
  });

  const totalIngressos = useMemo(() => data.ingressos.reduce((acc, curr) => acc + curr.import, 0), [data.ingressos]);
  const totalDespeses = useMemo(() => data.despeses.reduce((acc, curr) => acc + curr.import, 0), [data.despeses]);
  const balanç = totalIngressos - totalDespeses;
  const ratioEstalvi = ((balanç / totalIngressos) * 100).toFixed(1);

  const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  return (
    <div className="min-h-screen bg-slate-50 p-4 md:p-8 font-sans text-slate-900">
      <div className="max-w-6xl mx-auto">
        
        {/* Capçalera Familiar */}
        <header className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-6 bg-white p-6 rounded-3xl shadow-sm border border-slate-100">
          <div className="flex items-center gap-4">
            <div className="bg-indigo-600 p-3 rounded-2xl text-white shadow-lg shadow-indigo-200">
              <Users size={28} />
            </div>
            <div>
              <h1 className="text-2xl md:text-3xl font-bold text-slate-800">Hola, Jose Manuel i Alba</h1>
              <p className="text-slate-500 flex items-center gap-2">
                <Calendar size={14} /> Economia de la llar · Febrer 2026
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <button className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-slate-100 text-slate-700 px-5 py-2.5 rounded-xl font-medium hover:bg-slate-200 transition text-sm">
              Exportar
            </button>
            <button className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-indigo-600 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-indigo-700 transition shadow-lg shadow-indigo-100 text-sm">
              <PlusCircle size={18} /> Nou Moviment
            </button>
          </div>
        </header>

        {/* Mètriques Clau */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card 
            title="Balanç Familiar" 
            value={`${balanç.toLocaleString()} €`} 
            subtitle="Capacitat d'estalvi aquest mes"
            icon={<Wallet className="text-indigo-600" />}
            bgColor="bg-indigo-50"
            isPositive={balanç > 0}
          />
          <Card 
            title="Ingressos Totals" 
            value={`${totalIngressos.toLocaleString()} €`} 
            subtitle="Lloguer, Alba i Jose Manuel"
            icon={<ArrowUpRight className="text-emerald-600" />}
            bgColor="bg-emerald-50"
          />
          <Card 
            title="Despeses Totals" 
            value={`${totalDespeses.toLocaleString()} €`} 
            subtitle="Compte: Hipoteca i Deutes"
            icon={<ArrowDownRight className="text-rose-600" />}
            bgColor="bg-rose-50"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Secció Gràfics i Llistes */}
          <div className="lg:col-span-2 space-y-8">
            {/* Gràfic Evolució */}
            <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-100">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-lg font-bold flex items-center gap-2 text-slate-800">
                  <TrendingUp size={20} className="text-indigo-600" /> Salut Financera
                </h3>
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400 bg-slate-50 px-3 py-1 rounded-full">
                  Últims 6 mesos
                </span>
              </div>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.historics}>
                    <defs>
                      <linearGradient id="colorEstalvi" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.1}/>
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="mes" axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} />
                    <Tooltip 
                      contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.1)', padding: '12px' }}
                    />
                    <Area type="monotone" dataKey="estalvi" stroke="#6366f1" strokeWidth={4} fillOpacity={1} fill="url(#colorEstalvi)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Detall Moviments */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-100">
                <h3 className="text-md font-bold mb-4 text-slate-700">Entrades</h3>
                <div className="space-y-3">
                  {data.ingressos.map((ing, i) => (
                    <div key={i} className="flex items-center justify-between p-3 bg-slate-50 rounded-2xl border border-slate-100">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-white rounded-xl shadow-sm text-emerald-600">
                          {ing.icona}
                        </div>
                        <div>
                          <p className="text-sm font-bold">{ing.nom}</p>
                          <p className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">{ing.categoria}</p>
                        </div>
                      </div>
                      <p className="font-bold text-emerald-600">+{ing.import}€</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-100">
                <h3 className="text-md font-bold mb-4 text-slate-700">Principals Despeses</h3>
                <div className="space-y-3">
                  {data.despeses.slice(0, 4).map((des, i) => (
                    <div key={i} className="flex items-center justify-between p-3 hover:bg-slate-50 rounded-2xl transition">
                      <div className="flex items-center gap-3">
                        <div className={`w-2 h-2 rounded-full bg-indigo-400`} />
                        <div>
                          <p className="text-sm font-semibold">{des.nom}</p>
                          <p className="text-[10px] text-slate-400 font-bold tracking-tight">{des.categoria}</p>
                        </div>
                      </div>
                      <p className="font-bold text-slate-700">-{des.import}€</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Secció Assessor AI i Fites */}
          <div className="space-y-6">
            {/* Caixa Assessor IA */}
            <div className="bg-indigo-900 text-white p-6 rounded-3xl shadow-xl shadow-indigo-200 relative overflow-hidden">
              <div className="relative z-10">
                <div className="flex items-center gap-2 mb-6">
                  <div className="p-2 bg-indigo-500/30 rounded-lg">
                    <PiggyBank size={20} className="text-indigo-200" />
                  </div>
                  <h3 className="text-lg font-bold italic">Consell de l'Assessor</h3>
                </div>
                
                <div className="space-y-5">
                  <p className="text-indigo-100 leading-snug">
                    "Jose Manuel i Alba, el vostre ratio d'estalvi és del <span className="text-white font-black">{ratioEstalvi}%</span>. Una base molt sòlida per al vostre futur."
                  </p>
                  
                  <ul className="space-y-3">
                    <li className="flex gap-3 items-start bg-indigo-800/40 p-3 rounded-2xl">
                      <CheckCircle size={18} className="text-emerald-400 shrink-0 mt-0.5" />
                      <span className="text-xs text-indigo-50">Heu enviat correctament la reclamació a la DGSFP. Molt bé!</span>
                    </li>
                    <li className="flex gap-3 items-start bg-amber-500/20 p-3 rounded-2xl border border-amber-500/20">
                      <AlertTriangle size={18} className="text-amber-400 shrink-0 mt-0.5" />
                      <span className="text-xs text-indigo-50">El préstec de 165€ és la vostra prioritat de liquidació.</span>
                    </li>
                    <li className="flex gap-3 items-start bg-indigo-800/40 p-3 rounded-2xl">
                      <Info size={18} className="text-indigo-300 shrink-0 mt-0.5" />
                      <span className="text-xs text-indigo-50">Recordeu que el juny caldrà liquidar l'IRPF del lloguer.</span>
                    </li>
                  </ul>
                  
                  <button className="w-full py-3 bg-white text-indigo-900 rounded-2xl font-bold hover:bg-indigo-50 transition shadow-lg text-sm">
                    Revisar Estratègia Completa
                  </button>
                </div>
              </div>
              <div className="absolute -bottom-12 -right-12 w-48 h-48 bg-indigo-500/10 rounded-full blur-3xl"></div>
            </div>

            {/* Fons d'Emergència */}
            <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-100">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-sm font-bold uppercase tracking-widest text-slate-400">Objectiu Familiar</h3>
                <TrendingUp size={16} className="text-emerald-500" />
              </div>
              <div className="p-5 bg-emerald-50 rounded-2xl border border-emerald-100">
                <div className="flex justify-between items-center mb-2">
                  <p className="text-sm font-bold text-emerald-900 tracking-tight">Fons d'Emergència</p>
                  <span className="text-xs font-black text-emerald-600 bg-white px-2 py-0.5 rounded-lg border border-emerald-100">49%</span>
                </div>
                <div className="flex justify-between items-baseline mb-4">
                  <h4 className="text-2xl font-black text-slate-800">2.450 €</h4>
                  <p className="text-xs font-bold text-slate-400">de 5.000 €</p>
                </div>
                <div className="w-full bg-white h-3 rounded-full overflow-hidden p-0.5">
                  <div className="bg-emerald-500 h-full rounded-full transition-all duration-1000" style={{ width: '49%' }}></div>
                </div>
              </div>
              <p className="mt-4 text-[10px] text-center text-slate-400 font-medium leading-relaxed">
                Amb el balanç actual de {balanç}€, assolireu l'objectiu en aproximadament 4 mesos.
              </p>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
};

const Card = ({ title, value, subtitle, icon, bgColor, isPositive = true }) => (
  <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-100 flex items-start justify-between relative overflow-hidden group hover:shadow-md transition-shadow">
    <div className="relative z-10">
      <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">{title}</p>
      <h4 className={`text-2xl font-black mb-1 ${!isPositive && title.includes('Balanç') ? 'text-rose-600' : 'text-slate-800'}`}>{value}</h4>
      <p className="text-[10px] text-slate-500 font-medium">{subtitle}</p>
    </div>
    <div className={`p-4 rounded-2xl ${bgColor} transition-transform group-hover:scale-110 duration-300`}>
      {icon}
    </div>
  </div>
);

export default App;