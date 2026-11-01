module bin2gray_tb
#(
  parameter int Width = 8
)
(
  input  logic [Width-1:0] c0_bin_i,
  output logic [Width-1:0] c0_gray_o
);

bin2gray #(.Width(Width))
u_bin2gray (.c0_bin_i, .c0_gray_o);

endmodule
