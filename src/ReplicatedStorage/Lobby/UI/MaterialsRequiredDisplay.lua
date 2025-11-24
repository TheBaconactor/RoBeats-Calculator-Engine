-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:52 PM
-- Cached decompilation

return {
    ["new"] = function(_, p_u_1) --[[ Name: new ]] --[[ Line: 2 ]]
        local v2 = {}
        local v_u_3 = nil
        local v_u_4 = nil
        local v_u_5 = nil
        v2.cons = function(_) --[[ Name: cons ]] --[[ Line: 7 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_1, (ref 3): v_u_4, (ref 4): v_u_5 ]]
            v_u_3 = p_u_1.Icon
            v_u_4 = p_u_1.NameDisplay
            v_u_5 = p_u_1.CountDisplay
        end;
        v2.set_visible = function(_, p6) --[[ Name: set_visible ]] --[[ Line: 13 ]]
            --[[ Upvalues: (copy 1): p_u_1 ]]
            p_u_1.Visible = p6
        end;
        v2.set_info = function(_, p7, p8, p9, p10, p11) --[[ Name: set_info ]] --[[ Line: 17 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_4, (ref 3): v_u_5 ]]
            v_u_3.Image = p8
            v_u_4.Text = p7
            v_u_4.TextColor3 = p9
            v_u_5.Text = string.format("(%d/%d)", p10, p11)
            if p11 <= p10 then
                v_u_5.TextColor3 = Color3.fromRGB(0, 255, 0)
            else
                v_u_5.TextColor3 = Color3.fromRGB(255, 0, 0)
            end;
        end;
        v2:cons()
        return v2;
    end
};
