import React, { useEffect, useState } from 'react';
import styled from 'styled-components';

const LogsContainer = styled.div`
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
`;

const Th = styled.th`
  padding: 12px;
  text-align: left;
  border-bottom: 2px solid #e0e0e0;
  background-color: #f8f9fa;
`;

const Td = styled.td`
  padding: 12px;
  border-bottom: 1px solid #e0e0e0;
`;

const LogsPage = () => {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const storedLogs = JSON.parse(localStorage.getItem('actionLogs')) || [];
    setLogs(storedLogs);
  }, []);

  return (
    <LogsContainer>
      <h1>Activity Logs</h1>
      <Table>
        <thead>
          <tr>
            <Th>Timestamp</Th>
            <Th>User</Th>
            <Th>Role</Th>
            <Th>Action Type</Th>
            <Th>Details</Th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log, index) => (
            <tr key={index}>
              <Td>{new Date(log.timestamp).toLocaleString()}</Td>
              <Td>{log.user}</Td>
              <Td>{log.role}</Td>
              <Td>{log.type}</Td>
              <Td>{log.details}</Td>
            </tr>
          ))}
        </tbody>
      </Table>
    </LogsContainer>
  );
};

export default LogsPage;