import { useParams } from 'react-router-dom';
import Header from '../components/Header';

function DocumentPage() {
  const { id } = useParams();

  return (
    <div className="page">
      <Header />
      <main className="container">
        <h1>Document Page (Protected): {id}</h1>
      </main>
    </div>
  );
}

export default DocumentPage;
