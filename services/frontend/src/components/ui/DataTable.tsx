import React from 'react';
import './DataTable.css';

interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (item: T) => void;
}

export function DataTable<T>({ columns, data, onRowClick }: DataTableProps<T>) {
  return (
    <div className="data-table-container">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key}>{col.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="data-table-empty">
                NO DATA AVAILABLE
              </td>
            </tr>
          ) : (
            data.map((item, index) => (
              <tr 
                key={index} 
                onClick={() => onRowClick && onRowClick(item)}
                className={onRowClick ? 'clickable' : ''}
              >
                {columns.map((col) => (
                  <td key={col.key}>
                    {col.render ? col.render(item) : (item as any)[col.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
