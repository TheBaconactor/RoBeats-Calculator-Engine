-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:54 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRect)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
return {
    ["new"] = function(_, p_u_4, p_u_5) --[[ Name: new ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_2 ]]
        local v6 = {}
        local v_u_7 = nil
        local v_u_8 = nil
        v6.cons = function(_) --[[ Name: cons ]] --[[ Line: 17 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_5, (ref 3): v_u_8, (ref 4): v_u_1 ]]
            v_u_7 = Instance.new("Frame")
            v_u_7.Name = "SPChatWindowTextButton"
            v_u_7.Parent = p_u_5
            v_u_8 = Instance.new("TextLabel")
            v_u_8.BackgroundTransparency = v_u_1:tra(0)
            v_u_8.Selectable = false
            v_u_8.Font = Enum.Font.SourceSansBold
            v_u_8.TextXAlignment = Enum.TextXAlignment.Center
            v_u_8.TextYAlignment = Enum.TextYAlignment.Center
            v_u_8.Parent = v_u_7
        end;
        v6.set_frame_position = function(p9, p10) --[[ Name: set_frame_position ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7.Position = p10
            return p9;
        end;
        v6.set_frame_size = function(p11, p12) --[[ Name: set_frame_size ]] --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7.Size = p12
            return p11;
        end;
        v6.set_frame_anchor_point = function(p13, p14) --[[ Name: set_frame_anchor_point ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7.AnchorPoint = p14
            return p13;
        end;
        v6.set_frame_color = function(p15, p16) --[[ Name: set_frame_color ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            v_u_7.BackgroundColor3 = p16
            return p15;
        end;
        local v_u_17 = 0
        v6.set_frame_alpha = function(p18, p19) --[[ Name: set_frame_alpha ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_7, (ref 3): v_u_1 ]]
            v_u_17 = p19
            v_u_7.BackgroundTransparency = v_u_1:tra(p19)
            return p18;
        end;
        v6.get_frame_absolute_size = function(_) --[[ Name: get_frame_absolute_size ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7.AbsoluteSize;
        end;
        v6.get_frame = function(_) --[[ Name: get_frame ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7;
        end;
        v6.get_text = function(_) --[[ Name: get_text ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            return v_u_8;
        end;
        v6.set_font_size = function(p20, p21) --[[ Name: set_font_size ]] --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            v_u_8.TextSize = p21
            return p20;
        end;
        v6.set_font_color = function(p22, p23) --[[ Name: set_font_color ]] --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            v_u_8.TextColor3 = p23
            return p22;
        end;
        v6.set_text_message = function(p24, p25) --[[ Name: set_text_message ]] --[[ Line: 46 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            v_u_8.Text = p25
            return p24;
        end;
        v6.set_text_position = function(p26, p27) --[[ Name: set_text_position ]] --[[ Line: 47 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            v_u_8.Position = p27
            return p26;
        end;
        v6.set_text_size = function(p28, p29) --[[ Name: set_text_size ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            v_u_8.Size = p29
            return p28;
        end;
        v6.set_zindex = function(p30, p31) --[[ Name: set_zindex ]] --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_8 ]]
            v_u_7.ZIndex = p31
            v_u_8.ZIndex = p31 + 1
            return p30;
        end;
        local v_u_32 = nil
        v6.set_clicked_fn = function(p33, p34) --[[ Name: set_clicked_fn ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            v_u_32 = p34
            return p33;
        end;
        local v_u_35 = nil
        v6.set_update_fn = function(p36, p37) --[[ Name: set_update_fn ]] --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_35 ]]
            v_u_35 = p37
            return p36;
        end;
        local v_u_38 = true
        v6.set_visible = function(_, p39) --[[ Name: set_visible ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_7 ]]
            if v_u_38 ~= p39 then
                v_u_38 = p39
                v_u_7.Visible = v_u_38
            end;
        end;
        v6.set_alpha = function(_, p40) --[[ Name: set_alpha ]] --[[ Line: 65 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_1, (ref 3): v_u_3, (ref 4): v_u_17, (ref 5): v_u_8 ]]
            v_u_7.BackgroundTransparency = v_u_1:tra(v_u_3:Lerp(0, v_u_17, p40))
            v_u_8.TextTransparency = v_u_1:tra(v_u_3:Lerp(0, 1, p40))
            v_u_8.TextStrokeTransparency = v_u_1:tra(v_u_3:Lerp(0, 0.25, p40))
        end;
        local v_u_41 = v_u_2:new()
        v6.update = function(_, p_u_42) --[[ Name: update ]] --[[ Line: 72 ]]
            --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_35, (ref 3): v_u_1, (ref 4): v_u_7, (copy 5): v_u_41, (copy 6): p_u_4, (ref 7): v_u_32 ]]
            if v_u_38 == true then
                if v_u_35 then
                    pcall(function() --[[ Line: 75 ]]
                        --[[ Upvalues: (ref 1): v_u_35, (copy 2): p_u_42 ]]
                        v_u_35(p_u_42)
                    end)
                end;
                local v43 = v_u_1:get_cursor_nxy()
                v_u_1:get_ui_object_nrect(v_u_7, v_u_41)
                if p_u_4._chat:do_press_trigger() and (v_u_41:contains_vec2(v43) and v_u_32) then
                    v_u_32()
                end;
            end;
        end;
        v6:cons()
        return v6;
    end
};
