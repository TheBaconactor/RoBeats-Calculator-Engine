-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:35 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.SPRect)
require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_3 = require(game.ReplicatedStorage.Menu.CharacterDialogue)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Menu.SPUIChildUniqueSystemButton)
return {
    ["new"] = function(_, p_u_5, _) --[[ Name: new ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_2 ]]
        local v6 = v_u_3.Adapter:new()
        local v_u_7 = nil
        local v_u_8 = nil
        local v_u_9 = nil
        local v_u_10 = nil
        local v_u_11 = nil
        local v_u_12 = nil
        local v_u_13 = nil
        local v_u_14 = Vector3.new()
        local v_u_15 = nil
        local v_u_16 = 1
        local v_u_17 = false
        local v_u_18 = v_u_1:new()
        local v_u_19 = v_u_1:new()
        v6.get_unique_system_buttons = function(_) --[[ Name: get_unique_system_buttons ]] --[[ Line: 38 ]]
            --[[ Upvalues: (copy 1): v_u_18 ]]
            return v_u_18;
        end;
        v6.get_unique_system_buttons_enabled_fns = function(_) --[[ Name: get_unique_system_buttons_enabled_fns ]] --[[ Line: 39 ]]
            --[[ Upvalues: (copy 1): v_u_19 ]]
            return v_u_19;
        end;
        local function _() end;
        v_u_4:get_base_fn(v6, "get_native_size")
        v6.get_native_size = function(_) --[[ Name: get_native_size ]] --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            return v_u_14;
        end;
        v_u_4:get_base_fn(v6, "get_size")
        v6.get_size = function(_) --[[ Name: get_size ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            if v_u_8 then
                return v_u_8.Size;
            else
                return Vector3.new();
            end;
        end;
        v6.create_popup_on_character = function(_, p20, p21, p22) --[[ Name: create_popup_on_character ]] --[[ Line: 57 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_7, (ref 3): v_u_8, (ref 4): v_u_14, (ref 5): v_u_9, (ref 6): v_u_11, (ref 7): v_u_2, (ref 8): v_u_12, (ref 9): v_u_13 ]]
            v_u_15 = p21
            v_u_7 = p20:Clone()
            v_u_7.Parent = v_u_15
            v_u_8 = v_u_7.Part
            v_u_14 = v_u_8.Size
            v_u_9 = v_u_8.SurfaceGui
            v_u_11 = v_u_2:first_child_of_type(v_u_15, "Humanoid")
            v_u_12 = v_u_11.RootPart
            v_u_13 = v_u_12.Position
            v_u_9.Enabled = false
            if p22 then
                p22(v_u_8)
            end;
        end;
        v6.get_obj = function(_) --[[ Name: get_obj ]] --[[ Line: 76 ]]
            --[[ Upvalues: (ref 1): v_u_7 ]]
            return v_u_7;
        end;
        local v_u_23 = Vector3.new(0, 5.5, 0)
        v6.set_position_offset = function(p24, p25) --[[ Name: set_position_offset ]] --[[ Line: 79 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23 = p25
            return p24;
        end;
        v6.popup_update_visual = function(_, p26) --[[ Name: popup_update_visual ]] --[[ Line: 82 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_23, (ref 3): v_u_2, (copy 4): p_u_5, (ref 5): v_u_17, (ref 6): v_u_10, (ref 7): v_u_7, (ref 8): v_u_14, (ref 9): v_u_16, (copy 10): v_u_18 ]]
            local v27 = v_u_13 + v_u_23
            local v28 = (v27 - v_u_2:get_camera_cframe().p):Dot(v_u_2:get_camera_cframe().lookVector)
            local l_magnitude_0 = (v27 - v_u_2:get_localplayer_cframe().p).magnitude
            local v29 = p_u_5._menus:get_top_element()
            local v30 = v29 == nil and true or v29:swallows_input()
            local v31
            if v28 > 0 and l_magnitude_0 < 25 then
                v31 = v30 == false
            else
                v31 = false
            end;
            v_u_17 = v31
            if v31 == true then
                local v32 = v_u_2:lookat_camera_cframe(v27, p_u_5._spui)
                local v33 = false
                if v_u_10 == nil then
                    v33 = true
                    v_u_10 = v32
                elseif v_u_2:cframe_delta(v_u_10, v32) > 0.001 then
                    v33 = true
                    v_u_10 = v32
                end;
                if v33 == true then
                    v_u_7.Part.CFrame = v32
                end;
                local v34 = v_u_14 * v_u_16
                if (v34 - v_u_7.Part.Size).magnitude > 0.01 then
                    v_u_7.Part.Size = v34
                end;
                for v35 = 1, v_u_18:count() do
                    v_u_18:get(v35):update(p26)
                end;
            end;
        end;
        v6.set_scale = function(_, p36) --[[ Name: set_scale ]] --[[ Line: 127 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            v_u_16 = p36
        end;
        v6.should_show = function(_) --[[ Name: should_show ]] --[[ Line: 131 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17;
        end;
        local v_u_37 = false
        v6.set_enabled = function(_, p38) --[[ Name: set_enabled ]] --[[ Line: 134 ]]
            --[[ Upvalues: (ref 1): v_u_37, (ref 2): v_u_9, (copy 3): v_u_18, (copy 4): v_u_19 ]]
            if p38 ~= v_u_37 then
                v_u_37 = p38
                v_u_9.Enabled = v_u_37
                for v39 = 1, v_u_18:count() do
                    v_u_18:get(v39):set_visible(v_u_37)
                    if v_u_37 then
                        v_u_18:get(v39):set_enabled(v_u_19:get(v39)())
                    end;
                end;
            end;
        end;
        v6.update = function(p40, p41) --[[ Name: update ]] --[[ Line: 147 ]]
            p40:popup_update_visual(p41)
        end;
        v6.do_remove = function(_) --[[ Name: do_remove ]] --[[ Line: 151 ]]
            --[[ Upvalues: (copy 1): v_u_18, (ref 2): v_u_2, (ref 3): v_u_7, (ref 4): v_u_8, (ref 5): v_u_9, (ref 6): v_u_10, (ref 7): v_u_11, (ref 8): v_u_12, (ref 9): v_u_13, (ref 10): v_u_15 ]]
            v_u_18:clear()
            v_u_2:ptry(function() --[[ Line: 153 ]]
                --[[ Upvalues: (ref 1): v_u_7 ]]
                v_u_7:Destroy()
            end)
            v_u_7 = nil
            v_u_8 = nil
            v_u_9 = nil
            v_u_10 = nil
            v_u_11 = nil
            v_u_12 = nil
            v_u_13 = nil
            v_u_15 = nil
        end;
        return v6;
    end
};
