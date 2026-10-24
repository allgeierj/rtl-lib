module delay
#(
  parameter type DataType = logic,
  parameter int Depth = 1,
  parameter bit ResetEn = 1'b0,
  localparam int ArrayDepth = (Depth > 0) ? Depth : 1
)
(
  input logic clk,
  input logic rst = 1'b0,
  input DataType c0_data_i,
  output DataType cX_data_o 
);

if(Depth < 0) $error("Depth must be >= 0 (got %0d)", Depth);

typedef struct packed {
  DataType [0:ArrayDepth-1] delay_line;
} delay_state_ts;
delay_state_ts reg_d, reg_q = '0;

// Pass through if Depth == 0
assign cX_data_o = (Depth > 0) ? reg_q.delay_line[Depth-1] : c0_data_i;

always_comb begin
  reg_d = reg_q;
  reg_d.delay_line[0] = c0_data_i;
  for(int i = Depth - 1; i > 0; i--) begin
    reg_d.delay_line[i] = reg_q.delay_line[i-1];
  end
end

always_ff @(posedge clk) begin
  reg_q <= reg_d;
  if(ResetEn && rst) reg_q <= '0;
end

endmodule
