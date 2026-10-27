// Per-bit rising/falling/either edge pulses on c0_detect_i, valid when c0_valid_o is high.
// Outputs are combinational from c0_detect_i; c0_detect_i must be synchronous to clk.
module edge_detect
#(
  parameter int Width = 1
)
(
  input logic clk,
  input logic clk_en = 1'b1,
  input logic rst = 1'b0,
  input logic [Width-1:0] c0_detect_i,
  output logic c0_valid_o,
  output logic [Width-1:0] c0_rising_o,
  output logic [Width-1:0] c0_falling_o,
  output logic [Width-1:0] c0_either_o
);

if(Width < 1) $error("Width must be >= 1 (got %0d)", Width);

typedef struct packed {
  logic [Width-1:0] prev_detect;
} edge_detect_state_ts;
edge_detect_state_ts reg_d, reg_q = '0;

always_comb begin
  reg_d = reg_q;
  reg_d.prev_detect = c0_detect_i;

  c0_valid_o = clk_en & ~rst;
  
  c0_rising_o = ~reg_q.prev_detect & c0_detect_i;
  c0_falling_o = reg_q.prev_detect & ~c0_detect_i;
  c0_either_o = c0_rising_o | c0_falling_o;
end

always_ff @(posedge clk) begin
  if(clk_en) reg_q <= reg_d;
  if(rst) reg_q.prev_detect <= c0_detect_i;
end

endmodule
