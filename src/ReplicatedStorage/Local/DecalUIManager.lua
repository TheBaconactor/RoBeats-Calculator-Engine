-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:27 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_5 = require(game.ReplicatedStorage.Shared.Note2DSettings)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugConfig)
return {
    ["new"] = function(_, p_u_9) --[[ Name: new ]] --[[ Line: 15 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_8, (copy 3): v_u_7, (copy 4): v_u_3, (copy 5): v_u_2, (copy 6): v_u_5, (copy 7): v_u_6, (copy 8): v_u_4 ]]
        local v_u_10 = {}
        local v_u_11 = nil
        local v_u_12 = nil
        v_u_10.get_screengui = function(_) --[[ Name: get_screengui ]] --[[ Line: 20 ]]
            --[[ Upvalues: (ref 1): v_u_12 ]]
            return v_u_12;
        end;
        local v_u_13 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_1, (ref 3): v_u_8, (ref 4): v_u_11, (ref 5): v_u_7, (ref 6): v_u_12, (copy 7): v_u_10 ]]
            v_u_13 = v_u_1:screen_size()
            if v_u_8.AlwaysUseSurfaceGuiForDecalUIRootGame == true then
                v_u_11 = game.ReplicatedStorage.WorldUIProto.WorldUINormalPlane:Clone()
                v_u_11.Parent = v_u_7:get_world_ui_folder()
                v_u_12 = v_u_11.Surface.SurfaceGui
                v_u_12.Name = v_u_1:gen_name("DecalUIManager")
                v_u_12.AlwaysOnTop = true
            else
                v_u_12 = Instance.new("ScreenGui", game.Players.LocalPlayer.PlayerGui)
                v_u_12.IgnoreGuiInset = true
                v_u_12.Name = v_u_1:gen_name("DecalUIManager")
            end;
            v_u_10:calculate_screen_constants()
        end;
        local v_u_14 = v_u_3:new(0, 0)
        local v_u_15 = v_u_2:new()
        v_u_10.get_track_size_and_position = function(_) --[[ Name: get_track_size_and_position ]] --[[ Line: 48 ]]
            --[[ Upvalues: (copy 1): v_u_14, (copy 2): v_u_15 ]]
            return v_u_14, v_u_15;
        end;
        local function f_recalculate_surfacegui_normal_plane() --[[ Name: recalculate_surfacegui_normal_plane ]] --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_1, (copy 3): p_u_9, (ref 4): v_u_12 ]]
            if v_u_11 and v_u_11.PrimaryPart then
                local v16 = v_u_1:screen_size()
                v_u_11.PrimaryPart.Size = Vector3.new(p_u_9._spui:get_size_from_nxy(1, 1).X, p_u_9._spui:get_size_from_nxy(1, 1).Y, 0)
                v_u_11:SetPrimaryPartCFrame(p_u_9._spui:get_cframe())
                v_u_12.CanvasSize = v16
            end;
        end;
        local v_u_17 = false
        v_u_10.calculate_screen_constants = function(_) --[[ Name: calculate_screen_constants ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): f_recalculate_surfacegui_normal_plane, (copy 3): p_u_9, (ref 4): v_u_5, (copy 5): v_u_14, (copy 6): v_u_15, (ref 7): v_u_17 ]]
            local v18 = v_u_1:screen_size()
            f_recalculate_surfacegui_normal_plane()
            local v19 = 0.25
            local v20 = 0.5
            local v21 = 0.3
            if p_u_9.es_gamelocal_get_local_tracksystem then
                local v22 = p_u_9:es_gamelocal_get_local_tracksystem()
                if v22 then
                    local v23, _ = v22:get_player_note2d_settings()
                    if v23 ~= v_u_5.Width.Default then
                        if v23 == v_u_5.Width["A Bit Wider (x1.15)"] then
                            v19 = v19 * 1.15
                            v20 = v20 * 1.15
                            v21 = v21 * 1.15
                        elseif v23 == v_u_5.Width["Wider (x1.25)"] then
                            v19 = v19 * 1.25
                            v20 = v20 * 1.25
                            v21 = v21 * 1.25
                        elseif v23 == v_u_5.Width["Even Wider (x1.5)"] then
                            v19 = v19 * 1.5
                            v20 = v20 * 1.5
                            v21 = v21 * 1.5
                        elseif v23 == v_u_5.Width["Widest (x2)"] then
                            v19 = v19 * 2
                            v20 = v20 * 2
                            v21 = v21 * 2
                        elseif v23 == v_u_5.Width["A Bit More Narrow (x0.85)"] then
                            v19 = v19 * 0.85
                            v20 = v20 * 0.85
                            v21 = v21 * 0.85
                        elseif v23 == v_u_5.Width["Narrow (x0.75)"] then
                            v19 = v19 * 0.75
                            v20 = v20 * 0.75
                            v21 = v21 * 0.75
                        elseif v23 == v_u_5.Width["Narrowest (x0.5)"] then
                            v19 = v19 * 0.5
                            v20 = v20 * 0.5
                            v21 = v21 * 0.5
                        end;
                    end;
                end;
            end;
            local v24 = v_u_1:clamp(v19, 0, 1)
            local v25 = v_u_1:clamp(v20, 0, 1)
            local v26 = v_u_1:clamp(v21, 0, 1)
            local v27 = v18.X * v24
            if v18.Y * v25 < v27 then
                v27 = v18.Y * v25
            end;
            if v27 < v18.Y * v26 then
                v27 = v18.Y * v26
            end;
            v_u_14:set(v27 * 0.25, v18.Y)
            local v28 = v18.X * 0.5 - v27 * 0.5
            v_u_15:clear()
            v_u_15:push_back(v28)
            local v29 = v28 + v_u_14._x
            v_u_15:push_back(v29)
            local v30 = v29 + v_u_14._x
            v_u_15:push_back(v30)
            v_u_15:push_back(v30 + v_u_14._x)
            v_u_17 = true
        end;
        v_u_10.get_start_end_point_for_track_system_index = function(p31, p32, p33) --[[ Name: get_start_end_point_for_track_system_index ]] --[[ Line: 142 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_9, (ref 3): v_u_5, (ref 4): v_u_6, (ref 5): v_u_4 ]]
            local v34 = v_u_1:screen_size()
            local v35, v36 = p31:get_track_size_and_position()
            local v37 = v36:get(p33) + v35._x * 0.5
            local v38 = 0
            local v39 = 0
            local l__x_0 = v35._x
            if p_u_9.es_gamelocal_get_local_tracksystem then
                local v40 = p_u_9:es_gamelocal_get_local_tracksystem()
                if v40 then
                    local _, v41 = v40:get_player_note2d_settings()
                    local _, v42 = p32:get_player_note_display_mode_and_decal_id()
                    if v41 == v_u_5.Position.Default then
                        l__x_0 = v35._x
                    elseif v41 == v_u_5.Position["A Bit Higher (x1.25)"] then
                        l__x_0 = v35._x * 1.25
                    elseif v41 == v_u_5.Position["Higher (x1.5)"] then
                        l__x_0 = v35._x * 1.5
                    elseif v41 == v_u_5.Position["Even Higher (x2)"] then
                        l__x_0 = v35._x * 2
                    elseif v41 == v_u_5.Position["Highest (x3)"] then
                        l__x_0 = v35._x * 3
                    elseif v41 == v_u_5.Position["Mid-Screen"] then
                        l__x_0 = v34.Y * 0.5
                    elseif v41 == v_u_5.Position.Lowest then
                        l__x_0 = v35._x * v_u_6:singleton():get_info_for_id(v42):get_note_size_scale() * 0.5
                    end;
                end;
            end;
            local v43 = p32:get_active_note_display_mode()
            if v43 == v_u_4.DecalDown then
                v38 = -v35._x
                l__x_0 = v34.Y - l__x_0
            elseif v43 == v_u_4.DecalUp then
                v38 = v34.Y
            else
                l__x_0 = v39
            end;
            return Vector2.new(v37, v38), Vector2.new(v37, l__x_0);
        end;
        local v_u_44 = false
        v_u_10.raise_ui_recalculate = function(_) --[[ Name: raise_ui_recalculate ]] --[[ Line: 196 ]]
            --[[ Upvalues: (ref 1): v_u_44 ]]
            return v_u_44;
        end;
        v_u_10.update = function(p45, _) --[[ Name: update ]] --[[ Line: 198 ]]
            --[[ Upvalues: (ref 1): v_u_44, (ref 2): v_u_13, (ref 3): v_u_1, (ref 4): v_u_17, (copy 5): f_recalculate_surfacegui_normal_plane ]]
            v_u_44 = false
            if v_u_13 ~= v_u_1:screen_size() then
                v_u_13 = v_u_1:screen_size()
                p45:calculate_screen_constants()
            end;
            if v_u_17 then
                v_u_17 = false
                v_u_44 = true
            end;
            f_recalculate_surfacegui_normal_plane()
        end;
        v_u_10.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 211 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_11 ]]
            for _, v46 in pairs(v_u_12:GetChildren()) do
                v46.Parent = nil
            end;
            v_u_12:Destroy()
            if v_u_11 then
                v_u_11:Destroy()
                v_u_11 = nil
            end;
        end;
        f_cons()
        return v_u_10;
    end
};
