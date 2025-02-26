import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import styled, { createGlobalStyle } from 'styled-components';


const USERS = {
    admin: { password: 'admin123', role: 'admin', loginLog: [] },
    manager: { password: 'manager123', role: 'manager', loginLog: [] },
    attendant: { password: 'attendant123', role: 'attendant', loginLog: [] }
  };

const GlobalStyle = createGlobalStyle`
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
  
  body {
    margin: 0;
    padding: 0;
    font-family: 'Inter', sans-serif;
  }
`;

const Container = styled.div`
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #f8f9fa, #e9ecef);
  display: flex;
  justify-content: center;
  align-items: center;
`;

const LoginCard = styled.div`
  width: 400px;
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
`;

const Title = styled.h1`
  color: #1a1a1a;
  font-size: 24px;
  margin: 0 0 30px 0;
  font-weight: 600;
`;

const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 20px;
`;

const InputGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
`;

const Label = styled.label`
  color: #4a4a4a;
  font-size: 14px;
  font-weight: 500;
`;

const Input = styled.input`
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-size: 14px;
  color: #1a1a1a;

  &:focus {
    outline: none;
    border-color: #2d2d2d;
  }
`;

const Button = styled.button`
  padding: 12px;
  background: #1a1a1a;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  margin-top: 10px;

  &:hover {
    background: #2d2d2d;
  }
`;

const ErrorMessage = styled.div`
  color: #dc3545;
  font-size: 14px;
  margin-top: 10px;
`;

function Login({ setAuth }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = (e) => {
    e.preventDefault();
    const user = USERS[username];
    
    if (user && user.password === password) {
      user.loginLog.push(new Date().toISOString());
      localStorage.setItem('auth', JSON.stringify({ 
        username, 
        role: user.role,
        loginTime: new Date().toISOString() 
      }));
      setAuth({ username, role: user.role });
      navigate('/');
    } else {
      setError('Invalid username or password');
    }
  };

  return (
    <>
      <GlobalStyle />
      <Container>
        <LoginCard>
          <Title>Login</Title>
          <Form onSubmit={handleLogin}>
            <InputGroup>
              <Label>Username</Label>
              <Input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </InputGroup>

            <InputGroup>
              <Label>Password</Label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </InputGroup>

            {error && <ErrorMessage>{error}</ErrorMessage>}
            <Button type="submit">Sign In</Button>
          </Form>
        </LoginCard>
      </Container>
    </>
  );
}

export default Login;