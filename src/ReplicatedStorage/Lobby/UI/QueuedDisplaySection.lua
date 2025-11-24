-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:53 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.AudioData.SongDatabase)
return {
    ["new"] = function(_, p_u_2) --[[ Name: new ]] --[[ Line: 3 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v3 = {}
        local v_u_4 = nil
        local v_u_5 = nil
        local v_u_6 = nil
        local v_u_7 = nil
        local v_u_8 = nil
        local v_u_9 = nil
        local v_u_10 = nil
        local v_u_11 = v_u_1:invalid_songkey()
        v3.get_section_root = function(_) --[[ Name: get_section_root ]] --[[ Line: 14 ]]
            --[[ Upvalues: (copy 1): p_u_2 ]]
            return p_u_2;
        end;
        v3.set_song_title_display = function(_, p12) --[[ Name: set_song_title_display ]] --[[ Line: 15 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            v_u_4 = p12
        end;
        v3.set_artist_display = function(_, p13) --[[ Name: set_artist_display ]] --[[ Line: 16 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            v_u_5 = p13
        end;
        v3.set_cover_and_overlay_image = function(_, p14, p15) --[[ Name: set_cover_and_overlay_image ]] --[[ Line: 17 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7 ]]
            v_u_6 = p14
            v_u_7 = p15
        end;
        v3.set_time_remaining_display = function(_, p16) --[[ Name: set_time_remaining_display ]] --[[ Line: 18 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            v_u_8 = p16
        end;
        v3.set_queued_by_display = function(_, p17) --[[ Name: set_queued_by_display ]] --[[ Line: 19 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            v_u_9 = p17
        end;
        v3.set_queue_status_display = function(_, p18) --[[ Name: set_queue_status_display ]] --[[ Line: 20 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            v_u_10 = p18
        end;
        v3.set_visible = function(_, p19) --[[ Name: set_visible ]] --[[ Line: 22 ]]
            --[[ Upvalues: (copy 1): p_u_2 ]]
            p_u_2.Visible = p19
        end;
        v3.set_songid = function(_, p20) --[[ Name: set_songid ]] --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_4, (ref 3): v_u_1, (ref 4): v_u_5, (ref 5): v_u_6, (ref 6): v_u_7 ]]
            v_u_11 = p20
            v_u_4.Text = v_u_1:singleton():get_title_for_key(p20)
            v_u_5.Text = v_u_1:singleton():get_artist_for_key(p20)
            v_u_1:singleton():render_coverimage_for_key(v_u_6, v_u_7, p20)
        end;
        v3.get_songid = function(_) --[[ Name: get_songid ]] --[[ Line: 29 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11;
        end;
        v3.set_time_remaining_text = function(_, p21) --[[ Name: set_time_remaining_text ]] --[[ Line: 30 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            v_u_8.Text = p21
        end;
        v3.set_queued_by_text = function(_, p22) --[[ Name: set_queued_by_text ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            v_u_9.Text = p22
        end;
        v3.set_queue_status_text = function(_, p23) --[[ Name: set_queue_status_text ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            v_u_10.Text = p23
        end;
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = nil
        local v_u_27 = nil
        local v_u_28 = nil
        v3.set_vote_bar_section = function(_, p29, p30, p31, p32, p33) --[[ Name: set_vote_bar_section ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25, (ref 3): v_u_26, (ref 4): v_u_27, (ref 5): v_u_28 ]]
            v_u_24 = p29
            v_u_25 = p30
            v_u_26 = p31
            v_u_27 = p32
            v_u_28 = p33
        end;
        local v_u_34 = Vector2.new(437, 24)
        local v_u_35 = Vector2.new(478, 30)
        local v_u_36 = Vector2.new(16, 36)
        v3.update_vote_bar_fill = function(_, p37, p38) --[[ Name: update_vote_bar_fill ]] --[[ Line: 47 ]]
            --[[ Upvalues: (ref 1): v_u_24, (copy 2): v_u_34, (copy 3): v_u_35, (copy 4): v_u_36, (ref 5): v_u_25, (ref 6): v_u_26, (ref 7): v_u_27 ]]
            if v_u_24 ~= nil then
                local v39 = p37 + p38
                local v40 = v39 <= 0 and 1 or p37 / v39
                v_u_24.ImageRectSize = v_u_34 * Vector2.new(v40, 1)
                v_u_24.Size = UDim2.new(0, v_u_35.X * v40, 0, v_u_35.Y)
                v_u_24.Position = UDim2.new(0, v_u_36.X, 0, v_u_36.Y)
                local v41 = 1 - v40
                v_u_25.ImageRectSize = v_u_34 * Vector2.new(v41, 1)
                v_u_25.Size = UDim2.new(0, v_u_35.X * v41, 0, v_u_35.Y)
                v_u_25.ImageRectOffset = Vector2.new(v_u_34.X * v40, 0)
                v_u_25.Position = UDim2.new(0, v_u_36.X + v_u_35.X * v40, 0, v_u_36.Y)
                v_u_26.Text = string.format("%d \240\159\145\141", p37)
                v_u_27.Text = string.format("%d \240\159\145\142", p38)
            end;
        end;
        v3.update_vote_to_skip_count = function(_, p42) --[[ Name: update_vote_to_skip_count ]] --[[ Line: 68 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            if v_u_28 == nil then
                return;
            elseif p42 == 0 then
                v_u_28.Text = "Skipping song..."
            else
                v_u_28.Text = string.format("%d more downvote(s) to skip", p42)
            end;
        end;
        return v3;
    end
};
