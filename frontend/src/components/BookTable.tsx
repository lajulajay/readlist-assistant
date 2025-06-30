import React from "react";
import { Book } from "../types";

const BookTable: React.FC<{ books: Book[] }> = ({ books }) => (
  <table style={{ width: "100%", borderCollapse: "collapse" }}>
    <thead>
      <tr>
        <th>Title</th>
        <th>Author</th>
        <th>Summary</th>
        <th>Genre</th>
        <th>Ratings</th>
        <th>Avg Rating</th>
      </tr>
    </thead>
    <tbody>
      {books.map((book, i) => (
        <tr key={i}>
          <td>
            {book.source_url ? (
              <a href={book.source_url} target="_blank" rel="noopener noreferrer">
                {book.title}
              </a>
            ) : (
              book.title
            )}
          </td>
          <td>{book.author}</td>
          <td>{book.summary || ""}</td>
          <td>{book.genre || ""}</td>
          <td>{book.num_ratings || ""}</td>
          <td>{book.avg_rating || ""}</td>
        </tr>
      ))}
    </tbody>
  </table>
);

export default BookTable;