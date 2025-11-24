-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:53 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRect)
local s_GuiService_0 = game:GetService("GuiService")
return {
    ["new"] = function(_, p_u_4, p_u_5) --[[ Name: new ]] --[[ Line: 8 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): s_GuiService_0, (copy 3): v_u_3, (copy 4): v_u_1 ]]
        local v6 = {}
        local v_u_7 = nil
        local v_u_8 = nil
        local v_u_9 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 15 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_2, (ref 3): v_u_8, (ref 4): s_GuiService_0, (ref 5): v_u_9 ]]
            local l_ScreenGui_0 = Instance.new("ScreenGui", game.Players.LocalPlayer.PlayerGui)
            v_u_7 = l_ScreenGui_0
            l_ScreenGui_0.ResetOnSpawn = false
            l_ScreenGui_0.DisplayOrder = 1
            v_u_2:ptry(function() --[[ Line: 20 ]]
                --[[ Upvalues: (copy 1): l_ScreenGui_0 ]]
                l_ScreenGui_0.ScreenInsets = Enum.ScreenInsets.TopbarSafeInsets
            end)
            l_ScreenGui_0.Name = "ChatTopBar"
            local l_Frame_0 = Instance.new("Frame", l_ScreenGui_0)
            v_u_8 = l_Frame_0
            l_Frame_0.BackgroundColor3 = Color3.new(0, 0, 0)
            l_Frame_0.BackgroundTransparency = 1
            l_Frame_0.Size = UDim2.new(0, 35, 0, 38)
            l_Frame_0.Position = UDim2.new(0, 0, 0, 16)
            v_u_2:ptry(function() --[[ Line: 34 ]]
                --[[ Upvalues: (ref 1): s_GuiService_0, (copy 2): l_Frame_0 ]]
                local v10, _ = s_GuiService_0:GetGuiInset()
                l_Frame_0.Position = UDim2.new(0, 4, 0, v10.Y - 38)
            end)
            l_Frame_0.Active = true
            v_u_9 = Instance.new("ImageLabel", l_Frame_0)
            v_u_9.BackgroundTransparency = 1
            v_u_9.Size = UDim2.new(0, 35, 0, 33)
            v_u_9.Position = UDim2.new(0, 0, 0, 4)
            v_u_9.AnchorPoint = Vector2.new(0, 0)
        end;
        v6.post_create = function(p_u_11) --[[ Name: post_create ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_5, (ref 3): v_u_7 ]]
            v_u_2:ptry(function() --[[ Line: 50 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_5, (ref 3): v_u_7, (copy 4): p_u_11 ]]
                if v_u_2:do_disable_chat() then
                    p_u_5:set_visible(false)
                    v_u_7.Parent = nil
                end;
                p_u_11:update_image_state()
            end)
        end;
        v6.toggle_chat_active = function(p12) --[[ Name: toggle_chat_active ]] --[[ Line: 59 ]]
            --[[ Upvalues: (copy 1): p_u_5 ]]
            p_u_5:set_visible(not p_u_5:get_visible())
            p12:update_image_state()
        end;
        v6.update_image_state = function(_) --[[ Name: update_image_state ]] --[[ Line: 65 ]]
            --[[ Upvalues: (copy 1): p_u_5, (ref 2): v_u_9 ]]
            if p_u_5:get_visible() then
                v_u_9.Image = "rbxasset://textures/ui/Chat/ChatDown@2x.png"
            else
                v_u_9.Image = "rbxasset://textures/ui/Chat/Chat@2x.png"
            end;
        end;
        v6.get_frame_absolute_position = function(_) --[[ Name: get_frame_absolute_position ]] --[[ Line: 74 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            return v_u_8.AbsolutePosition;
        end;
        v6.get_frame_absolute_size = function(_) --[[ Name: get_frame_absolute_size ]] --[[ Line: 75 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            return v_u_8.AbsoluteSize;
        end;
        local v_u_13 = v_u_3:new()
        v6.update = function(p14, _) --[[ Name: update ]] --[[ Line: 78 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_9, (copy 3): v_u_13, (copy 4): p_u_4, (ref 5): v_u_1 ]]
            if not v_u_2:do_disable_chat() then
                local v15 = v_u_2:get_cursor_nxy()
                v_u_2:get_ui_object_nrect(v_u_9, v_u_13)
                if p_u_4._input:control_just_pressed(v_u_1.KEY_CLICK) and v_u_13:contains_vec2(v15) then
                    p14:toggle_chat_active()
                end;
                p14:update_image_state()
            end;
        end;
        f_cons()
        return v6;
    end
};
